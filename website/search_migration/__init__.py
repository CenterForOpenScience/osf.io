JSON_UPDATE_NODES_SQL = """
SELECT json_agg(
    json_build_object(
        '_type', CASE
                 WHEN N.type = 'osf.registration'
                   THEN 'registration'
                 WHEN PREPRINT.URL IS NOT NULL
                   THEN 'preprint'
                 WHEN PARENT_GUID._id IS NULL
                   THEN 'project'
                 ELSE 'component'
                 END
        , '_index', '{index}'
        , 'doc_as_upsert', TRUE
        , '_id', NODE_GUID._id
        , '_op_type', 'update'
        , 'doc', json_build_object(
            'contributors', (SELECT json_agg(json_build_object(
                                                 'url', CASE
                                                        WHEN U.is_active
                                                          THEN '/' || USER_GUID._id || '/'
                                                        ELSE NULL
                                                        END
                                                 , 'fullname', U.fullname
                                             ))
                             FROM osf_osfuser AS U
                               INNER JOIN osf_contributor AS CONTRIB
                                 ON (U.id = CONTRIB.user_id)
                               LEFT OUTER JOIN osf_guid AS USER_GUID
                                 ON (U.id = USER_GUID.object_id AND (USER_GUID.content_type_id = (SELECT id FROM django_content_type WHERE model = 'osfuser')))
                             WHERE (CONTRIB.node_id = N.id AND CONTRIB.visible = TRUE))
            , 'extra_search_terms', CASE
                                    WHEN strpos(N.title, '-') + strpos(N.title, '_') + strpos(N.title, '.') > 0
                                      THEN translate(N.title, '-_.', '   ')
                                    ELSE ''
                                    END
            , 'normalized_title', N.title
            , 'registered_date', N.registered_date
            , 'id', NODE_GUID._id
            , 'category', CASE
                          WHEN N.type = 'osf.registration'
                            THEN 'registration'
                          WHEN PREPRINT.URL IS NOT NULL
                            THEN 'preprint'
                          WHEN PARENT_GUID._id IS NULL
                            THEN 'project'
                          ELSE 'component'
                          END
            , 'title', N.title
            , 'parent_id', PARENT_GUID._id
            , 'embargo_end_date', EMBARGO.DATA ->> 'end_date'
            , 'is_pending_registration', CASE
                                         WHEN N.type = 'osf.registration'
                                           THEN REGISTRATION_APPROVAL.PENDING
                                         ELSE FALSE
                                         END
            , 'is_pending_embargo', EMBARGO.DATA ->> 'pending'
            , 'is_registration', N.type = 'osf.registration'
            , 'is_pending_retraction', RETRACTION.state = 'pending'
            , 'is_retracted', RETRACTION.state = 'approved'
            , 'preprint_url', PREPRINT.URL
            , 'boost', CASE
                       WHEN N.type = 'osf.node'
                         THEN 2
                       ELSE 1
                       END
            , 'public', N.is_public
            , 'description', N.description
            , 'tags', (CASE
                       WHEN TAGS.names IS NOT NULL
                       THEN TAGS.names
                       ELSE
                         '{{}}'::TEXT[]
                       END)
                , 'affiliated_institutions', (SELECT array_agg(INST.name)
                                          FROM osf_institution AS INST
                                            INNER JOIN osf_abstractnode_affiliated_institutions
                                              ON (INST.id = osf_abstractnode_affiliated_institutions.institution_id)
                                          WHERE osf_abstractnode_affiliated_institutions.abstractnode_id = N.id)
            , 'license', json_build_object(
                'text', LICENSE.text
                , 'name', LICENSE.name
                , 'id', LICENSE.license_id
                , 'copyright_holders', LICENSE.copyright_holders
                , 'year', LICENSE.year
            )
            , 'url', '/' || NODE_GUID._id || '/'
            , 'date_created', N.created
            , 'wikis', CASE
                       WHEN RETRACTION.state != 'approved'
                         THEN
                           (SELECT json_agg(json_build_object(
                                                translate(page_name, '.', ' '), content
                                            ))
                            FROM addons_wiki_nodewikipage
                              INNER JOIN osf_guid
                                ON (addons_wiki_nodewikipage.id = osf_guid.object_id AND
                                    (osf_guid.content_type_id = (SELECT id FROM django_content_type WHERE model = 'nodewikipage')))
                            WHERE osf_guid._id = ANY (SELECT p.value
                                                      FROM osf_abstractnode
                                                        INNER JOIN
                                                            jsonb_each_text(osf_abstractnode.wiki_pages_current) P
                                                          ON TRUE
                                                      WHERE id = N.id))
                       ELSE
                         '{{}}'::JSON
                       END
        )
    )
)
FROM osf_abstractnode AS N
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = N.id
                  AND content_type_id = (SELECT id FROM django_content_type WHERE model = 'abstractnode')
            LIMIT 1
            ) NODE_GUID ON TRUE
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = (
              SELECT parent_id
              FROM osf_noderelation
              WHERE child_id = N.id
                    AND is_node_link = FALSE
              LIMIT 1)
                  AND content_type_id = (SELECT id FROM django_content_type WHERE model = 'abstractnode')
            LIMIT 1
            ) PARENT_GUID ON TRUE
  LEFT JOIN LATERAL (
            SELECT array_agg(TAG.name) as names
            FROM osf_tag AS TAG
            INNER JOIN osf_abstractnode_tags ON (TAG.id = osf_abstractnode_tags.tag_id)
            WHERE (TAG.system = FALSE AND osf_abstractnode_tags.abstractnode_id = N.id)
            LIMIT 1
            ) TAGS ON TRUE
  LEFT JOIN LATERAL (
            SELECT
              osf_nodelicense.license_id,
              osf_nodelicense.name,
              osf_nodelicense.text,
              osf_nodelicenserecord.year,
              osf_nodelicenserecord.copyright_holders
            FROM osf_nodelicenserecord
              INNER JOIN osf_abstractnode ON (osf_nodelicenserecord.id = osf_abstractnode.node_license_id)
              LEFT OUTER JOIN osf_nodelicense ON (osf_nodelicenserecord.node_license_id = osf_nodelicense.id)
            WHERE osf_abstractnode.id = N.id
            ) LICENSE ON TRUE
  LEFT JOIN LATERAL (SELECT (
    CASE WHEN N.type = 'osf.registration'
      THEN
        (CASE WHEN N.retraction_id IS NOT NULL
          THEN
            (SELECT state
             FROM osf_retraction
             WHERE id = N.retraction_id)
         ELSE
           (WITH RECURSIVE ascendants AS (
             SELECT
               parent_id,
               child_id,
               1                AS LEVEL,
               ARRAY [child_id] AS cids,
               '' :: VARCHAR    AS state
             FROM osf_noderelation
             WHERE is_node_link IS FALSE AND child_id = N.id
             UNION ALL
             SELECT
               S.parent_id,
               D.child_id,
               D.level + 1,
               D.cids || S.child_id,
               R.state
             FROM ascendants AS D
               INNER JOIN osf_noderelation AS S
                 ON D.parent_id = S.child_id
               INNER JOIN osf_abstractnode AS A
                 ON D.child_id = A.id
               INNER JOIN osf_retraction AS R
                 ON A.retraction_id = R.id
             WHERE S.is_node_link IS FALSE
                   AND N.id = ANY (cids)
           ) SELECT state
             FROM ascendants
             WHERE child_id = N.id
                   AND state IS NOT NULL
             ORDER BY LEVEL ASC
             LIMIT 1)
         END)
    ELSE
      (SELECT '' :: VARCHAR AS state)
    END
  )) RETRACTION ON TRUE
  LEFT JOIN LATERAL (
            SELECT (
              CASE WHEN N.type = 'osf.registration'
                THEN (
                  CASE WHEN N.embargo_id IS NOT NULL
                    THEN (
                      SELECT json_build_object(
                                 'pending', state = 'unapproved',
                                 'end_date',
                                 CASE WHEN state = 'approved'
                                   THEN
                                     TO_CHAR(end_date, 'Day, Mon DD, YYYY')
                                 ELSE
                                   NULL
                                 END
                             ) AS DATA
                      FROM osf_retraction
                      WHERE id = N.retraction_id
                    )
                  ELSE (
                    WITH RECURSIVE ascendants AS (
                      SELECT
                        parent_id,
                        child_id,
                        1                                AS LEVEL,
                        ARRAY [child_id]                 AS cids,
                        '' :: VARCHAR                    AS state,
                        NULL :: TIMESTAMP WITH TIME ZONE AS end_date
                      FROM osf_noderelation
                      WHERE is_node_link IS FALSE AND child_id = N.id
                      UNION ALL
                      SELECT
                        S.parent_id,
                        D.child_id,
                        D.level + 1,
                        D.cids || S.child_id,
                        E.state,
                        E.end_date
                      FROM ascendants AS D
                        JOIN osf_noderelation AS S
                          ON D.parent_id = S.child_id
                        JOIN osf_abstractnode AS A
                          ON D.child_id = A.id
                        JOIN osf_embargo AS E
                          ON A.retraction_id = E.id
                      WHERE S.is_node_link IS FALSE
                            AND N.id = ANY (cids)
                    ) SELECT json_build_object(
                                 'pending', state = 'unapproved',
                                 'end_date',
                                 CASE WHEN state = 'approved'
                                   THEN
                                     TO_CHAR(end_date, 'Day, Mon DD, YYYY')
                                 ELSE
                                   NULL
                                 END
                             ) AS DATA
                      FROM ascendants
                      WHERE child_id = N.id
                            AND state IS NOT NULL
                      ORDER BY LEVEL ASC
                      LIMIT 1
                  ) END
                )
              ELSE (
                SELECT json_build_object(
                           'pending', FALSE,
                           'end_date', NULL
                       ) AS DATA
              ) END
            )
            ) EMBARGO ON TRUE
  LEFT JOIN LATERAL ( SELECT (
    CASE WHEN N.type = 'osf.registration' AND N.registration_approval_id IS NOT NULL
      THEN (
        SELECT state = 'unapproved' AS PENDING
        FROM osf_registrationapproval
        WHERE id = N.retraction_id
      )
    ELSE (
      SELECT FALSE AS PENDING
    ) END)
            ) REGISTRATION_APPROVAL ON TRUE
  LEFT JOIN LATERAL (
            SELECT
              CASE WHEN ((osf_abstractprovider.domain_redirect_enabled AND osf_abstractprovider.domain IS NOT NULL) OR
                         osf_abstractprovider._id = 'osf')
                THEN
                  '/' || (SELECT G._id
                          FROM osf_guid G
                          WHERE (G.object_id = P.id)
                                AND (G.content_type_id = (SELECT id FROM django_content_type WHERE model = 'preprintservice'))
                          ORDER BY created ASC, id ASC
                          LIMIT 1) || '/'
              ELSE
                '/preprints/' || osf_abstractprovider._id || '/' || (SELECT G._id
                                                                     FROM osf_guid G
                                                                     WHERE (G.object_id = P.id)
                                                                           AND (G.content_type_id = (SELECT id FROM django_content_type WHERE model = 'preprintservice'))
                                                                     ORDER BY created ASC, id ASC
                                                                     LIMIT 1) || '/'
              END AS URL
            FROM osf_preprintservice P
              INNER JOIN osf_abstractprovider ON P.provider_id = osf_abstractprovider.id
            WHERE P.node_id = N.id
              AND P.machine_state != 'initial'  -- is_preprint
              AND N.preprint_file_id IS NOT NULL
              AND N.is_public = TRUE
              AND N._is_preprint_orphan != TRUE
            ORDER BY P.is_published DESC, P.created DESC
            LIMIT 1
            ) PREPRINT ON TRUE
WHERE (TYPE = 'osf.node' OR TYPE = 'osf.registration' OR TYPE = 'osf.quickfilesnode')
  AND is_public IS TRUE
  AND is_deleted IS FALSE
  AND (spam_status IS NULL OR NOT (spam_status = 2 or (spam_status = 1 AND {spam_flagged_removed_from_search})))
  AND NOT (UPPER(N.title::text) LIKE UPPER('%Bulk stress 201%') OR UPPER(N.title::text) LIKE UPPER('%Bulk stress 202%') OR UPPER(N.title::text) LIKE UPPER('%OSF API Registration test%') -- is_qa_node
           OR N.id IN  -- Comes from website.settings.DO_NOT_INDEX_LIST
              (SELECT THRUTAGS.abstractnode_id
               FROM osf_abstractnode_tags THRUTAGS
                 INNER JOIN osf_tag TAGS ON (THRUTAGS.tag_id = TAGS.id)
               WHERE (TAGS.name = 'qatest'
                  OR TAGS.name = 'qa test')))
  AND NOT (N.id IN  -- node.archiving
           (SELECT AJ.dst_node_id  -- May need to be made recursive as AJ table grows
            FROM osf_archivejob AJ
            WHERE (AJ.status != 'FAILURE' AND AJ.status != 'SUCCESS'
                   AND AJ.dst_node_id IS NOT NULL)))
  AND id > {page_start}
  AND id <= {page_end}
LIMIT 1;
"""

JSON_UPDATE_FILES_SQL = """
SELECT json_agg(
    json_build_object(
        '_type', 'file'
        , '_index', '{index}'
        , 'doc_as_upsert', TRUE
        , '_id', F._id
        , '_op_type', 'update'
        , 'doc', json_build_object(
            'id', F._id
            , 'deep_url', CASE WHEN F.provider = 'osfstorage'
                          THEN '/' || (NODE.DATA ->> 'guid') || '/files/' || F.provider || '/' || F._id
                          ELSE '/' || (NODE.DATA ->> 'guid') || '/files/' || F.provider || F._path
                          END
            , 'guid_url', CASE WHEN FILE_GUID._id IS NOT NULL
                          THEN '/' || FILE_GUID._id || '/'
                          ELSE NULL
                          END
            , 'tags', (CASE
              WHEN TAGS.names IS NOT NULL
              THEN TAGS.names
              ELSE
                '{{}}'::TEXT[]
              END)
            , 'name', F.name
            , 'category', 'file'
            , 'node_url', '/' || (NODE.DATA ->> 'guid') || '/'
            , 'node_title', NODE.DATA ->> 'title'
            , 'parent_id', NODE.DATA ->> 'parent_guid'
            , 'is_registration', NODE.DATA ->> 'is_registration' = 'true' -- Weirdness from the lateral join causes this to be a string
            , 'is_retracted', NODE.DATA ->> 'is_retracted' = 'true' -- Weirdness from the lateral join causes this to be a string
            , 'extra_search_terms', CASE WHEN strpos(F.name, '-') + strpos(F.name, '_') + strpos(F.name, '.') > 0
                                    THEN translate(F.name, '-_.', '   ')
                                    ELSE ''
                                    END
        )
    )
)
FROM osf_basefilenode AS F
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = F.id
                  AND content_type_id = (SELECT id FROM django_content_type WHERE model = 'basefilenode')
            LIMIT 1
            ) FILE_GUID ON TRUE
  LEFT JOIN LATERAL (
            SELECT array_agg(TAG.name) AS names
            FROM osf_tag AS TAG
              INNER JOIN osf_basefilenode_tags ON (TAG.id = osf_basefilenode_tags.tag_id)
            WHERE (TAG.system = FALSE AND osf_basefilenode_tags.basefilenode_id = F.id)
      ) TAGS ON TRUE
  LEFT JOIN LATERAL (
            SELECT json_build_object(
                       'is_registration', (CASE WHEN N.type = 'osf.registration'
                                           THEN TRUE
                                           ELSE FALSE
                                           END)
                       , 'title', N.title
                       , 'guid', (SELECT _id
                                  FROM osf_guid
                                  WHERE object_id = N.id
                                        AND content_type_id = (SELECT id
                                                               FROM django_content_type
                                                               WHERE model = 'abstractnode')
                                  LIMIT 1)
                       , 'parent_guid', (SELECT _id
                                         FROM osf_guid
                                         WHERE object_id = (
                                           SELECT parent_id
                                           FROM osf_noderelation
                                           WHERE child_id = N.id
                                                 AND is_node_link = FALSE
                                           LIMIT 1)
                                               AND content_type_id = (SELECT id
                                                                      FROM django_content_type
                                                                      WHERE model = 'abstractnode')
                                         LIMIT 1)
                       , 'is_retracted', (CASE WHEN N.type = 'osf.registration'
                         THEN
                           (CASE WHEN N.retraction_id IS NOT NULL
                             THEN
                               (SELECT state = 'approved'
                                FROM osf_retraction
                                WHERE id = N.retraction_id)
                             ELSE
                              (WITH RECURSIVE ascendants AS (
                                SELECT
                                  parent_id,
                                  child_id,
                                  1                AS LEVEL,
                                  ARRAY [child_id] AS cids,
                                  FALSE            AS is_retracted
                                FROM osf_noderelation
                                WHERE is_node_link IS FALSE AND child_id = N.id
                                UNION ALL
                                SELECT
                                  S.parent_id,
                                  D.child_id,
                                  D.level + 1,
                                  D.cids || S.child_id,
                                  R.state = 'approved' AS is_retracted
                                FROM ascendants AS D
                                  INNER JOIN osf_noderelation AS S
                                    ON D.parent_id = S.child_id
                                  INNER JOIN osf_abstractnode AS A
                                    ON D.child_id = A.id
                                  INNER JOIN osf_retraction AS R
                                    ON A.retraction_id = R.id
                                WHERE S.is_node_link IS FALSE
                                      AND N.id = ANY (cids)
                              ) SELECT is_retracted
                                FROM ascendants
                                WHERE child_id = N.id
                                ORDER BY is_retracted DESC -- Put TRUE at the top
                                LIMIT 1)
                            END)
                         ELSE
                           FALSE
                         END)
                   ) AS DATA
            FROM osf_abstractnode N
            WHERE N.id = F.node_id
            LIMIT 1
            ) NODE ON TRUE
WHERE name IS NOT NULL
      AND name != ''
      AND node_id = ANY (SELECT id
                         FROM osf_abstractnode
                         WHERE (TYPE = 'osf.node' OR TYPE = 'osf.registration' OR TYPE = 'osf.quickfilesnode')
                               AND is_public IS TRUE
                               AND is_deleted IS FALSE
                               AND (spam_status IS NULL OR NOT (spam_status = 2 or (spam_status = 1 AND {spam_flagged_removed_from_search})))
                               AND NOT (UPPER(osf_abstractnode.title::text) LIKE UPPER('%Bulk stress 201%') OR UPPER(osf_abstractnode.title::text) LIKE UPPER('%Bulk stress 202%') OR UPPER(osf_abstractnode.title::text) LIKE UPPER('%OSF API Registration test%') -- is_qa_node
                                        OR "osf_abstractnode"."id" IN
                                          (SELECT THRUTAGS.abstractnode_id
                                           FROM osf_abstractnode_tags THRUTAGS
                                             INNER JOIN osf_tag TAGS ON (THRUTAGS.tag_id = TAGS.id)
                                           WHERE (TAGS.name = 'qatest'
                                              OR TAGS.name = 'qa test')))
                               AND NOT (osf_abstractnode.id IN
                                        (SELECT AJ.dst_node_id
                                         FROM osf_archivejob AJ
                                             WHERE (AJ.status != 'FAILURE' AND AJ.status != 'SUCCESS'
                                                AND AJ.dst_node_id IS NOT NULL)))
                        )
      AND id > {page_start}
      AND id <= {page_end}
LIMIT 1;
"""

JSON_UPDATE_USERS_SQL = """
SELECT json_agg(
    json_build_object(
        '_type', 'user'
        , '_index', '{index}'
        , 'doc_as_upsert', TRUE
        , '_id', USER_GUID._id
        , '_op_type', 'update'
        , 'doc', json_build_object(
            'id', USER_GUID._id
            , 'user', U.fullname
            , 'normalized_user', U.fullname
            , 'normalized_names', json_build_object(
                'fullname', U.fullname
                , 'given_name', U.given_name
                , 'family_name', U.family_name
                , 'middle_names', U.middle_names
                , 'suffix', U.suffix
            )
            , 'names', json_build_object(
                'fullname', U.fullname
                , 'given_name', U.given_name
                , 'family_name', U.family_name
                , 'middle_names', U.middle_names
                , 'suffix', U.suffix
            )
            , 'job', CASE
                     WHEN U.jobs :: JSON -> 0 -> 'institution' IS NOT NULL
                       THEN
                         (U.jobs :: JSON -> 0 -> 'institution') :: TEXT
                     ELSE
                       ''
                     END
            , 'job_title', (CASE
                            WHEN U.jobs :: JSON -> 0 -> 'title' IS NOT NULL
                              THEN
                                (U.jobs :: JSON -> 0 -> 'title') :: TEXT
                            ELSE
                              ''
                            END)
            , 'all_jobs', (SELECT array_agg(DISTINCT (JOB :: JSON -> 'institution') :: TEXT)
                           FROM
                             (SELECT json_array_elements(jobs :: JSON) AS JOB
                              FROM osf_osfuser
                              WHERE id = U.id
                             ) AS JOBS)
            , 'school', (CASE
                         WHEN U.schools :: JSON -> 0 -> 'institution' IS NOT NULL
                           THEN
                             (U.schools :: JSON -> 0 -> 'institution') :: TEXT
                         ELSE
                           ''
                         END)
            , 'all_schools', (SELECT array_agg(DISTINCT (SCHOOL :: JSON -> 'institution') :: TEXT)
                              FROM
                                (SELECT json_array_elements(schools :: JSON) AS SCHOOL
                                 FROM osf_osfuser
                                 WHERE id = U.id
                                ) AS SCHOOLS)
            , 'category', 'user'
            , 'degree', (CASE
                         WHEN U.schools :: JSON -> 0 -> 'degree' IS NOT NULL
                           THEN
                             (U.schools :: JSON -> 0 -> 'degree') :: TEXT
                         ELSE
                           ''
                         END)
            , 'social', (SELECT json_object_agg(
                key,
                (
                  CASE
                  WHEN key = 'orcid'
                    THEN 'http://orcid.org/' || value
                  WHEN key = 'github'
                    THEN 'http://github.com/' || value
                  WHEN key = 'scholar'
                    THEN 'http://scholar.google.com/citations?user=' || value
                  WHEN key = 'twitter'
                    THEN 'http://twitter.com/' || value
                  WHEN key = 'profileWebsites'
                    THEN value
                  WHEN key = 'linkedIn'
                    THEN 'https://www.linkedin.com/' || value
                  WHEN key = 'impactStory'
                    THEN 'https://impactstory.org/u/' || value
                  WHEN key = 'researcherId'
                    THEN 'http://researcherid.com/rid/' || value
                  WHEN key = 'researchGate'
                    THEN 'https://researchgate.net/profile/' || value
                  WHEN key = 'academiaInstitution'
                    THEN 'https://' || value
                  WHEN key = 'academiaProfileID'
                    THEN '.academia.edu/' || value
                  WHEN key = 'baiduScholar'
                    THEN 'http://xueshu.baidu.com/scholarID/' || value
                  WHEN key = 'ssrn'
                    THEN 'http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=' || value
                  END
                ))
                         FROM jsonb_each_text(
                             (SELECT social
                              FROM osf_osfuser
                              WHERE id = U.id)
                         )
                         WHERE value IS NOT NULL
                               AND value != ''
                               AND value != '[]'
            )
            , 'boost', 2
        )
    )
)
FROM osf_osfuser AS U
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = U.id
                  AND content_type_id = ANY (SELECT id
                                             FROM django_content_type
                                             WHERE model = 'osfuser')
            LIMIT 1
            ) USER_GUID ON TRUE
WHERE is_active = TRUE
      AND id > {page_start}
      AND id <= {page_end}
LIMIT 1;
"""

JSON_DELETE_NODES_SQL = """
SELECT json_agg(
    json_build_object(
        '_type', CASE
                 WHEN N.type = 'osf.registration'
                   THEN 'registration'
                 WHEN PREPRINT.is_preprint > 0
                   THEN 'preprint'
                 WHEN PARENT_GUID._id IS NULL
                   THEN 'project'
                 ELSE 'component'
                 END
        , '_index', '{index}'
        , '_id', NODE_GUID._id
        , '_op_type', 'delete'
    )
)
FROM osf_abstractnode AS N
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = N.id
                  AND content_type_id = (SELECT id FROM django_content_type WHERE model = 'abstractnode')
            LIMIT 1
            ) NODE_GUID ON TRUE
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = (
              SELECT parent_id
              FROM osf_noderelation
              WHERE child_id = N.id
                    AND is_node_link = FALSE
              LIMIT 1)
                  AND content_type_id = (SELECT id FROM django_content_type WHERE model = 'abstractnode')
            LIMIT 1
            ) PARENT_GUID ON TRUE
  LEFT JOIN LATERAL (
          SELECT COUNT(P.id) as is_preprint
          FROM osf_preprintservice P
          WHERE P.node_id = N.id
            AND P.machine_state != 'initial'
            AND N.preprint_file_id IS NOT NULL
            AND N.is_public = TRUE
            AND N._is_preprint_orphan != TRUE
          LIMIT 1
          ) PREPRINT ON TRUE
WHERE NOT ((TYPE = 'osf.node' OR TYPE = 'osf.registration' OR TYPE = 'osf.quickfilesnode')
  AND N.is_public IS TRUE
  AND N.is_deleted IS FALSE
  AND (spam_status IS NULL OR NOT (spam_status = 2 or (spam_status = 1 AND {spam_flagged_removed_from_search})))
  AND NOT (UPPER(N.title::text) LIKE UPPER('%Bulk stress 201%') OR UPPER(N.title::text) LIKE UPPER('%Bulk stress 202%') OR UPPER(N.title::text) LIKE UPPER('%OSF API Registration test%') -- is_qa_node
           OR N.id IN  -- Comes from website.settings.DO_NOT_INDEX_LIST
             (SELECT THRUTAGS.abstractnode_id
              FROM osf_abstractnode_tags THRUTAGS
                INNER JOIN osf_tag TAGS ON (THRUTAGS.tag_id = TAGS.id)
              WHERE (TAGS.name = 'qatest'
                 OR TAGS.name = 'qa test')))
  AND NOT (N.id IN  -- node.archiving
           (SELECT AJ.dst_node_id  -- May need to be made recursive as AJ table grows
            FROM osf_archivejob AJ
               WHERE (AJ.status != 'FAILURE' AND AJ.status != 'SUCCESS'
                   AND AJ.dst_node_id IS NOT NULL)))
  )
  AND id > {page_start}
  AND id <= {page_end}
LIMIT 1;
"""

JSON_DELETE_FILES_SQL = """
SELECT json_agg(json_build_object(
    '_type', 'file'
    , '_index', '{index}'
    , '_id', F._id
    , '_op_type', 'delete'
))
FROM osf_basefilenode AS F
WHERE NOT (name IS NOT NULL
      AND name != ''
      AND node_id = ANY (SELECT id
                         FROM osf_abstractnode
                         WHERE (TYPE = 'osf.node' OR TYPE = 'osf.registration' OR TYPE = 'osf.quickfilesnode')
                               AND is_public IS TRUE
                               AND is_deleted IS FALSE
                               AND (spam_status IS NULL OR NOT (spam_status = 2 or (spam_status = 1 AND {spam_flagged_removed_from_search})))
                               -- settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH
                               -- node.archiving or is_qa_node
                               AND NOT (UPPER(osf_abstractnode.title::text) LIKE UPPER('%Bulk stress 201%') OR UPPER(osf_abstractnode.title::text) LIKE UPPER('%Bulk stress 202%') OR UPPER(osf_abstractnode.title::text) LIKE UPPER('%OSF API Registration test%') -- is_qa_node
                                        OR "osf_abstractnode"."id" IN
                                          (SELECT THRUTAGS.abstractnode_id
                                           FROM osf_abstractnode_tags THRUTAGS
                                             INNER JOIN osf_tag TAGS ON (THRUTAGS.tag_id = TAGS.id)
                                           WHERE (TAGS.name = 'qatest'
                                              OR TAGS.name = 'qa test')))
                               AND NOT (osf_abstractnode.id IN
                                        (SELECT AJ.dst_node_id
                                         FROM osf_archivejob AJ
                                             WHERE (AJ.status != 'FAILURE' AND AJ.status != 'SUCCESS'
                                                AND AJ.dst_node_id IS NOT NULL)))
                        )
      )
      AND id > {page_start}
      AND id <= {page_end}
LIMIT 1;
"""

JSON_DELETE_USERS_SQL = """
SELECT json_agg(
    json_build_object(
        '_type', 'user'
        , '_index', '{index}'
        , '_id', USER_GUID._id
        , '_op_type', 'delete'
    )
)
FROM osf_osfuser AS U
  LEFT JOIN LATERAL (
            SELECT _id
            FROM osf_guid
            WHERE object_id = U.id
                  AND content_type_id = ANY (SELECT id
                                             FROM django_content_type
                                             WHERE model = 'osfuser')
            LIMIT 1
            ) USER_GUID ON TRUE
WHERE is_active != TRUE
  AND id > {page_start}
  AND id <= {page_end}
LIMIT 1;
"""

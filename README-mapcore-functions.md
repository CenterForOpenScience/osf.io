# NII GRDM - mAP core 連携機能用ライブラリ仕様

本文書は、「GRDM - mAP core連携機能」用のモジュールに用意されたクラス・関数などについて記述する。

## GRDM連携関数

1. mAP連携機能が有効であるかを返す
    ```
    def mapcore_sync_is_enabled():
    ```
    - 戻り値: bool 利用可能な場合にTrue

1. mAP連携機能を有効にし(状態をDB保存)
    ```
    def mapcore_sync_set_enabled():
    ```
    - 戻り値: なし

1. mAP連携機能を無効にする(状態をDB保存)
    ```
    def mapcore_sync_set_disabled():
    ```
    - 戻り値: なし

1. GRDM側を主としてmAP側に同期する
    ```
    def mapcore_sync_upload_all():
    ```
    - 戻り値: なし

1. ユーザーのAccess Tokenが有効であることを確認し、可能であれば更新する
    ```
    def mapcore_api_is_available(user):
    ```
    - user
      OSFUserオブジェクトでユーザーを指定する
    - 戻り値: 常にTrue
      更新できなかった場合はMAPCoreTokenExpired例外

1. GRDM ContiributorとmAPメンバーを比較して、追加・削除・権限変更するユーザーを求める
    ```
    def compare_members(rdm_members, map_members, to_map):
    ```
    - rdm_members
    RDMmemberの配列
    - map_members
    mAPメンバーを表す辞書(```get_group_members``が返すメンバー情報)
    - to_map
    「GRDM->mAP」同期のための比較を行う場合にTrue、「mAP->GRDM」同期の比較を行う場合にFalse
    - 戻り値
    4つのリストのタプル（追加するユーザのリスト、削除するユーザーのリスト、管理者とする一般ユーザーのリスト、
    一般ユーザーとする管理者のリスト）

1. mAP coreグループの詳細情報(メンバー情報を含まない)を取り出す
    ```
    def mapcore_get_group_detail_info(mapcore, group_key):
    ```
    - mapcore
    MAPCoreオブジェクト。ここに含まれるユーザーのトークンを使用して取り出しを試みる
    - group_key
    情報を取り出すmAPグループの識別子(group_key)

1. mAP coreグループの詳細情報(メンバー情報を含む)を取り出す
    ```
    def mapcore_get_extended_group_info(mapcore, group_key, base_grp=None, can_abort=True):
    ```
    - mapcore
    MAPCoreオブジェクト。ここに含まれるユーザーのトークンを使用してmAP coreにアクセスする
    - group_key
    情報を取り出すmAPグループの識別子(group_key)
    - base_grp
    既に基本的なグループ情報(```get_group_by_key```で得られるもの)を既に読み込み済みの場合に指定すると、再読み込みを省略する
    - can_abort
    Trueを指定すると、エラー発生時に例外をスローする。Falseを指定すると戻り値にFalseを返してエラーを通知する

1. mAPに新しいグループを作成する
    ```
    def mapcore_sync_map_new_group(user, node):
    ```
    - user
    mAPを操作するユーザーを指定するOSFUserオブジェクト。このユーザーは、mAPグループの管理者となる
    - node
    Nodeオブジェクトを指定する。node.titleが作成するmAPグループのタイトルとなる。

1. mAPグループに対応するGRDM Projectを新規に作成する
    ```
    def mapcore_create_new_node_from_mapgroup(mapcore, map_group):
    ```
    - mapcore
    MAPCoreオブジェクト。ここに含まれるユーザーのトークンを使用してmAP coreにアクセスする
    - map_group
    mAPグループ情報を保持する辞書(```get_group_by_key```で得られるもの)
    - mAPグループ管理者の誰か1名が、作成されたGRDM Projectのcreatorとなる
    - 本関数ではメンバー(Contributor)の同期は行われない

1. mAPグループからGRDM Projectへの同期を行う
    ```
    def mapcore_sync_rdm_project(node, title_desc=False, contributors=False, mapcore=None):
    ```
    - node
    同期を行うProjectをNodeオブジェクトで指定する
    - title_desc
    グループ情報(グループ名と説明)を同期する場合にTrueを指定する
    - contirbutors
    メンバー情報(Contributor)を同期する場合にTrueを指定する
    - mapcore
    MAPCoreオブジェクト。ここに含まれるユーザーのトークンを使用してmAP coreにアクセスする。
    省略した場合はNodeのCreatorのトークンが使用される

1. GRDM ProjectからmAPグループへの同期を行う
    ```
    def mapcore_sync_map_group(access_user, node, title_desc=True, contributors=True, lock_node=True):
    ```
    - access_user
    アクセスするユーザー。そのユーザーのアクセストークンを優先的に使う。
    - node
    同期を行うProjectをNodeオブジェクトで指定する
    - title_desc
    グループ情報(グループ名と説明)を同期する場合にTrueを指定する
    - contirbutors
    メンバー情報(Contributor)を同期する場合にTrueを指定する
    - lock_node
    Nodeでロックするかどうか。

1. mAPグループのメンバー情報にアクセスできるユーザーをGRDM Projectのcontributorから探す
    ```
    def mapcore_get_accessible_user(access_user, node):
    ```
    - access_user
    最初にアクセス可否を確認するユーザーを指定するOSFUserオブジェクト
    - node
    メンバーリストを得たいmAPグループに対応するProjectを指定するNodeオブジェクト
    - 戻り値
    access_user、Nodeのcreator、次いでcontributorを順にスキャンして、mAPグループのメンバー情報にアクセスできるユーザーを探し、
    見つかればそのOSFUserオブジェクトを返す。見つからない場合は、Noneを返す

1. あるユーザーが所属するグループをmAPとGRDMの両方から検索し、付き合わせて必要な同期処理を行う
    ```
    def mapcore_sync_rdm_my_projects(user):
    ```
    - user
    所属するユーザーを指定するOSFUserオブジェクト


## mAP coreトークンの取得に関わる関数

1. OAuth2によるトークン取得手続きを開始する
    ```
    def mapcore_request_authcode(**kwargs):
    ```
    - `kwargs['request']['next_uri']`に、OAuth2によるトークン取得処理が終わった後に戻るURL(ブラウザにRedirectで通知される)
     を指定する
    - 本関数は、手作業で /mapcore_oauth_start にアクセスした時にも呼び出される
    - 本関数を実行するとブラウザにリダイレクトが返されてリクエストが終了する

1. OAuth2によるトークン取得手続きを完了する
    ```
    def mapcore_receive_authcode(user, params):
    ```
    - 本関数は、OAuth2サーバー(mAP coreサーバー)が /mapcore_oauth_complete にアクセスした時に呼び出される
    - 本関数が実行されると、```mapcore_request_authcode```で指定したURLに対するリダイレクトをブラウザに送信して、リクエストを終了する

1. OAuth2手順の1つとして、Authorization CodeをAccess Tokenに交換する
    ```
    def mapcore_get_accesstoken(authcode, redirect):
    ```
    - ```mapcore_receive_authcode```の下位ルーチン

1. ユーザーのAccess Tokenを更新する
    ```
    def mapcore_refresh_accesstoken(user, force=False):
    ```
    - user
    OSFUserオブジェクトでユーザーを指定する
    - force
    トークンの有効/無効の確認を省略して、とにかくトークンの更新を行う

## 補助的なクラス

1. 排他制御のためのファイルロック機能
    ```
    class MAPCoreLocker():
    ```
    - 変更見込みのため詳細省略

1. 比較のためにGRDM側のcontributorを保持する
    ```
    class RDMmember(object):
    ```

## mAP core API利用クラス

```
class MAPCore(object):
```

メソッド毎の実行例(戻り値)を示す。
詳細な動作についてはmAP core Resource Server API仕様書を参照されたい。


1. コンストラクタ
    ```
    def __init__(self, user):
    ```
    - user
    OSFUserオブジェクトで、APIコール時に使用するアクセストークンを持つユーザーを指定する

1. トークンの更新
    ```
    def refresh_token(self):
    ```
    - Access Tokenの有効期間が切れていた場合に、Refresh Tokenを使用してトークンを更新する

1. mAP core APIバージョン番号の取得
    ```
    def mapcore.get_api_version()
    ```

    - 戻り値の例
    ```
    {u'result': {u'author': u'National Institute of Informatics',
                 u'release': u'2019-01-31',
                 u'revision': u'1.0.1',
                 u'version': 1},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. グループ名でグループを検索する
    ```
    def get_group_by_name(self, group_name):
    ```

    - 戻り値の例
    ```
    {u'result': {u'groups': [{u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-04-22 21:42:19',
                              u'group_admin': [u'\u9577\u539f\u5b8f\u6cbb'],
                              u'group_icon': 1,
                              u'group_icon_type': u'png',
                              u'group_key': u'112bdfc4-64fc-11e9-933d-066fa4512b0e',
                              u'group_name': u'Nagahara Test 002',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'Nagahara Test 002\r\nCreated on GRDM',
                              u'introduction_en': u'',
                              u'modified_at': u'2019-04-23 03:55:00',
                              u'open_member': 1,
                              u'public': 1}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. グループキーでグループを検索する
    ```
    def get_group_by_key(self, group_key):
    ```

    - 戻り値の例
    ```
    {u'result': {u'groups': [{u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-04-22 21:42:19',
                              u'group_admin': [u'\u9577\u539f\u5b8f\u6cbb'],
                              u'group_icon': 1,
                              u'group_icon_type': u'png',
                              u'group_key': u'112bdfc4-64fc-11e9-933d-066fa4512b0e',
                              u'group_name': u'Nagahara Test 002',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'Nagahara Test 002\r\nCreated on GRDM',
                              u'introduction_en': u'',
                              u'modified_at': u'2019-04-23 03:55:00',
                              u'open_member': 1,
                              u'public': 1}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. 新規のグループを作成する
    ```
    def create_group(self, group_name):
    ```

    - 戻り値の例
    ```
    {u'result': {u'groups': [{u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-05-03 17:33:03',
                              u'group_icon': 1,
                              u'group_icon_type': u'png',
                              u'group_key': u'113997f6-6d7e-11e9-a24a-066fa4512b0e',
                              u'group_name': u'TakoIkaTentsu',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'TakoIkaTentsu',
                              u'introduction_en': u'',
                              u'modified_at': u'2019-05-03 17:33:03',
                              u'open_member': 2,
                              u'public': 1}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. グループ属性(グループ名と説明文)を変更する
    ```
    def edit_group(self, group_key, group_name, introduction):
    ```

    - 戻り値の例
    ```
    {u'result': {u'groups': [{u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-04-22 21:42:19',
                              u'group_icon': 1,
                              u'group_icon_type': u'png',
                              u'group_key': u'112bdfc4-64fc-11e9-933d-066fa4512b0e',
                              u'group_name': u'FooBarHoge',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'Introduction',
                              u'introduction_en': u'',
                              u'modified_at': u'2019-05-03 17:34:55',
                              u'open_member': 2,
                              u'public': 1}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. グループを削除する
    ```
    def delete_group(self, group_key):
    ```

    - 戻り値の例
    ```
    {u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. グループのメンバーを取得する
    ```
    def get_group_members(self, group_key):
    ```

    - 戻り値の例
    ```
    {u'result': {u'accounts': [{u'account_name': u'\u9577\u539f\u5b8f\u6cbb',
                                u'admin': 2,
                                u'created_at': u'2019-03-19 21:20:57',
                                u'eppn': u'sample@openidp.nii.ac.jp',
                                u'mail': u'foo@example.co.jp',
                                u'modified_at': u'2019-03-19 21:50:55',
                                u'university': u'\u6709\u9650\u4f1a\u793e\u30a8\u30cc\u30fb\u30a8\u30b9\u30fb\u30d7\u30e9\u30f3\u30cb\u30f3\u30b0'},
                               {u'account_name': u'\u9577\u539f\u5b8f\u6cbb',
                                u'admin': 0,
                                u'created_at': u'2019-03-24 17:45:42',
                                u'eppn': u'hsample@openidp.nii.ac.jp',
                                u'mail': u'hiro@toriatama.com',
                                u'modified_at': u'2019-03-24 17:45:42',
                                u'university': u'\u6709\u6a29\u4f1a\u793e\u30a8\u30cc\u30fb\u30a8\u30a5\u30fb\u30d7\u30e9\u30f3\u30cb\u30f3\u30b0 \u958b\u767a\u5ba4'},
                               {u'account_name': u'\u9577\u539f\u5b8f\u6cbb',
                                u'admin': 0,
                                u'created_at': u'2019-04-17 16:46:26',
                                u'eppn': u'nsample@openidp.nii.ac.jp',
                                u'mail': u'sample@nspl.jp',
                                u'modified_at': u'2019-04-17 16:46:26',
                                u'university': u'NS\u30d7\u30e9\u30f3\u30cb\u30f3\u30b0 Dev Test'}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. ユーザーの所属グループのリストを取得する
    ```
    def get_my_groups(self):
    ```

    - 戻り値の例
    ```
    {u'result': {u'groups': [{u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-03-21 13:32:50',
                              u'group_admin': [u'\u9577\u539f\u5b8f\u6cbb'],
                              u'group_icon': 5,
                              u'group_icon_type': u'png',
                              u'group_key': u'grdm_map_connection_test01',
                              u'group_name': u'First Group',
                              u'group_name_en': u'mAP\u9023\u643a\u30c6\u30b9\u30c8\u752801',
                              u'inspect_join': 0,
                              u'introduction': u'GRDM - mAP\u9023\u643a\u30c6\u30b9\u30c8\u752801',
                              u'introduction_en': u'GRDM - mAP\u9023\u643a\u30c6\u30b9\u30c8\u752801',
                              u'modified_at': u'2019-04-23 04:17:05',
                              u'open_member': 1,
                              u'public': 1},
                             {u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-04-22 21:52:58',
                              u'group_admin': [u'\u9577\u539f\u5b8f\u6cbb'],
                              u'group_icon': 20,
                              u'group_icon_type': u'png',
                              u'group_key': u'nspl_test_001',
                              u'group_name': u'NSPL Test 001',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'NS Planning Test group 001\r\ncreated on Cloud Gateway',
                              u'introduction_en': None,
                              u'modified_at': u'2019-04-23 03:17:35',
                              u'open_member': 2,
                              u'public': 1},
                             {u'active': 1,
                              u'contact_admin': None,
                              u'contact_member': None,
                              u'created_at': u'2019-05-03 17:33:03',
                              u'group_admin': [u'\u9577\u539f\u5b8f\u6cbb'],
                              u'group_icon': 1,
                              u'group_icon_type': u'png',
                              u'group_key': u'113997f6-6d7e-11e9-a24a-066fa4512b0e',
                              u'group_name': u'TakoIkaTentsu',
                              u'group_name_en': u'',
                              u'inspect_join': 0,
                              u'introduction': u'TakoIkaTentsu',
                              u'introduction_en': u'',
                              u'modified_at': u'2019-05-03 17:33:03',
                              u'open_member': 2,
                              u'public': 1}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. ePPNで指定するユーザーをグループのメンバーとして追加する
    ```
    def add_to_group(self, group_key, eppn, admin):
    ```

    - 戻り値の例
    ```
    {u'result': {u'accounts': [{u'account_name': u'\u9577\u539f\u5b8f\u6cbb',
                                u'account_name_en': u'Nspl Nagahara',
                                u'agreement': None,
                                u'arrival': u'1',
                                u'arrival_key': None,
                                u'arrival_time': None,
                                u'created_at': u'2019-04-17 16:46:26',
                                u'eppn': u'nsample@openidp.nii.ac.jp',
                                u'idp_entity_id': None,
                                u'import': None,
                                u'introduction': None,
                                u'introduction_en': None,
                                u'language': u'ja',
                                u'mail': u'sample@nspl.jp',
                                u'modified_at': u'2019-04-17 16:46:26',
                                u'temporary': 0,
                                u'university': u'NS\u30d7\u30e9\u30f3\u30cb\u30f3\u30b0 Dev Test',
                                u'university_en': u'NS Planning Co., Ltd. '}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. ePPNで指定するユーザーをグループのメンバーから削除する
    ```
    def remove_from_group(self, group_key, eppn):
    ```

    - 戻り値の例
    ```
    {u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

1. ePPNで指定するユーザーの属性(管理者/一般メンバー)を変更する
    ```
    def edit_member(self, group_key, eppn, admin):
    ```

    - 戻り値の例
    ```
    {u'result': {u'accounts': [{u'account_name': u'\u9577\u539f\u5b8f\u6cbb',
                                u'account_name_en': u'Nspl Nagahara',
                                u'agreement': None,
                                u'arrival': u'1',
                                u'arrival_key': None,
                                u'arrival_time': None,
                                u'created_at': u'2019-04-17 16:46:26',
                                u'eppn': u'nsample@openidp.nii.ac.jp',
                                u'idp_entity_id': None,
                                u'import': None,
                                u'introduction': None,
                                u'introduction_en': None,
                                u'language': u'ja',
                                u'mail': u'sample@nspl.jp',
                                u'modified_at': u'2019-04-17 16:46:26',
                                u'temporary': 0,
                                u'university': u'NS\u30d7\u30e9\u30f3\u30cb\u30f3\u30b0 Dev Test',
                                u'university_en': u'NS Planning Co., Ltd. '}]},
     u'status': {u'error_code': 0, u'error_msg': u''}}
    ```

## 例外クラス
1. ベース
    ```
    class MAPCoreException(Exception):
    ```

1. mAP API呼び出し時にトークンがExpireしていた場合
    ```
    class MAPCoreTokenExpired(MAPCoreException):
    ```

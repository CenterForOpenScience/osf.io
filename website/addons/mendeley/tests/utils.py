# -*- coding: utf-8 -*-
import mock
from contextlib import contextmanager

from modularodm import storage

from framework.mongo import set_up_storage

from website.addons.base.testing import AddonTestCase
from website.addons.mendeley import MODELS

from json import dumps

def init_storage():
    set_up_storage(MODELS, storage_class=storage.MongoStorage)

    
mock_responses = {
    'folders': [
        {
            "id": "4901a8f5-9840-49bf-8a17-bdb3d5900417",
            "name": "subfolder",
            "created": "2015-02-13T20:34:42.000Z",
            "modified": "2015-02-13T20:34:44.000Z"
        },
        {
            "id": "a6b12ebf-bd07-4f4e-ad73-f9704555f032",
            "name": "subfolder2",
            "created": "2015-02-13T20:34:42.000Z",
            "modified": "2015-02-13T20:34:44.000Z",
            "parent_id": "4901a8f5-9840-49bf-8a17-bdb3d5900417"
        },
        {
            "id": "e843da05-8818-47c2-8c37-41eebfc4fe3f",
            "name": "subfolder3",
            "created": "2015-02-17T15:27:13.000Z",
            "modified": "2015-02-17T15:27:13.000Z",
            "parent_id": "a6b12ebf-bd07-4f4e-ad73-f9704555f032"
        }
    ],
    'documents': [
          {
                  "id": "547a1215-efdb-36d2-93b2-e3ef8991264f",
                  "title": "Cloud Computing",
                  "type": "journal",
                  "authors": [
                            {
                                        "first_name": "Shivaji P",
                                        "last_name": "Mirashe"
                                      },
                            {
                                        "first_name": "N V",
                                        "last_name": "Kalyankar"
                                      }
                          ],
                  "year": 2010,
                  "source": "Communications of the ACM",
                  "identifiers": {
                            "issn": "03621340",
                            "doi": "10.1145/358438.349303",
                            "pmid": "22988693",
                            "arxiv": "1003.4074",
                            "isbn": "1-58113-199-2"
                          },
                  "created": "2015-02-13T18:17:47.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-13T20:34:44.000Z",
                  "abstract": "Computing as you know it is about to change, your applications and documents are going to move from the desktop into the cloud. I'm talking about cloud computing, where applications and files are hosted on a \"cloud\" consisting of thousands of computers and servers, all linked together and accessible via the Internet. With cloud computing, everything you do is now web based instead of being desktop based. You can access all your programs and documents from any computer that's connected to the Internet. How will cloud computing change the way you work? For one thing, you're no longer tied to a single computer. You can take your work anywhere because it's always accessible via the web. In addition, cloud computing facilitates group collaboration, as all group members can access the same programs and documents from wherever they happen to be located. Cloud computing might sound far-fetched, but chances are you're already using some cloud applications. If you're using a web-based email program, such as Gmail or Hotmail, you're computing in the cloud. If you're using a web-based application such as Google Calendar or Apple Mobile Me, you're computing in the cloud. If you're using a file- or photo-sharing site, such as Flickr or Picasa Web Albums, you're computing in the cloud. It's the technology of the future, available to use today."
                },
          {
                  "id": "5e95a1a9-d789-3576-9943-35eee8e59ea9",
                  "title": "The Google file system",
                  "type": "generic",
                  "authors": [
                            {
                                        "first_name": "Sanjay",
                                        "last_name": "Ghemawat"
                                      },
                            {
                                        "first_name": "Howard",
                                        "last_name": "Gobioff"
                                      },
                            {
                                        "first_name": "Shun-Tak",
                                        "last_name": "Leung"
                                      }
                          ],
                  "year": 2003,
                  "source": "ACM SIGOPS Operating Systems Review",
                  "identifiers": {
                            "pmid": "191",
                            "issn": "01635980"
                          },
                  "created": "2015-02-13T18:17:48.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-13T20:34:44.000Z",
                  "abstract": "We have designed and implemented the Google File System, a scalable distributed file system for large distributed data-intensive applications. It provides fault tolerance while running on inexpensive commodity hardware, and it delivers high aggregate performance to a large number of clients. While sharing many of the same goals as previous distributed file systems, our design has been driven by observations of our application workloads and technological environment, both current and anticipated, that reflect a marked departure from some earlier file system assumptions. This has led us to reexamine traditional choices and explore radically different design points. The file system has successfully met our storage needs. It is widely deployed within Google as the storage platform for the generation and processing of data used by our service as well as research and development efforts that require large data sets. The largest cluster to date provides hundreds of terabytes of storage across thousands of disks on over a thousand machines, and it is concurrently accessed by hundreds of clients. In this paper, we present file system interface extensions designed to support distributed applications, discuss many aspects of our design, and report measurements from both micro-benchmarks and real world use."
                },
          {
                  "id": "3480056e-fe4d-339b-afed-4312d03739a4",
                  "title": "Above the clouds: A Berkeley view of cloud computing",
                  "type": "journal",
                  "authors": [
                            {
                                        "first_name": "M",
                                        "last_name": "Armbrust"
                                      },
                            {
                                        "first_name": "A",
                                        "last_name": "Fox"
                                      },
                            {
                                        "first_name": "R",
                                        "last_name": "Griffith"
                                      },
                            {
                                        "first_name": "AD",
                                        "last_name": "Joseph"
                                      },
                            {
                                        "last_name": "RH"
                                      }
                          ],
                  "year": 2009,
                  "source": "  University of California, Berkeley, Tech. Rep. UCB ",
                  "identifiers": {
                            "pmid": "11242594",
                            "arxiv": "0521865719 9780521865715"
                          },
                  "keywords": [
                            "cloud computing",
                            "distributed system economics",
                            "internet datacenters",
                            "utility computing"
                          ],
                  "created": "2015-02-13T18:17:48.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-13T20:34:45.000Z",
                  "abstract": "Cloud Computing, the long-held dream of computing as a utility, has the potential to transform a large part of the  IT industry, making software even more attractive as a service and shaping the way IT hardware is designed and  purchased. Developers with innovative ideas for new Internet services no longer require the large capital outlays  in hardware to deploy their service or the human expense to operate it. They need not be concerned about over-  provisioning for a service whose popularity does not meet their predictions, thus wasting costly resources, or under-  provisioning for one that becomes wildly popular, thus missing potential customers and revenue. Moreover, companies  with large batch-oriented tasks can get results as quickly as their programs can scale, since using 1000 servers for one  hour costs no more than using one server for 1000 hlarge scale, is unprecedented in the history of IT.  "
                },
          {
                  "id": "e917dd51-8b94-3748-810b-cafa2accc18a",
                  "title": "Toward the next generation of recommender systems: A survey of the state-of-the-art and possible extensions",
                  "type": "generic",
                  "authors": [
                            {
                                        "first_name": "Gediminas",
                                        "last_name": "Adomavicius"
                                      },
                            {
                                        "first_name": "Alexander",
                                        "last_name": "Tuzhilin"
                                      }
                          ],
                  "year": 2005,
                  "source": "IEEE Transactions on Knowledge and Data Engineering",
                  "identifiers": {
                            "issn": "10414347",
                            "pmid": "1423975",
                            "arxiv": "3"
                          },
                  "keywords": [
                            "Collaborative filtering",
                            "Extensions to recommander systems",
                            "Rating estimation methods",
                            "Recommander systems"
                          ],
                  "created": "2015-02-13T18:17:48.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-13T20:34:45.000Z",
                  "abstract": " This paper presents an overview of the field of recommender systems and describes the current generation of recommendation methods that are usually classified into the following three main categories: content-based, collaborative, and hybrid recommendation approaches. This paper also describes various limitations of current recommendation methods and discusses possible extensions that can improve recommendation capabilities and make recommender systems applicable to an even broader range of applications. These extensions include, among others, an improvement of understanding of users and items, incorporation of the contextual information into the recommendation process, support for multicriteria ratings, and a provision of more flexible and less intrusive types of recommendations."
                },
          {
                  "id": "8cd60008-888a-3212-966f-29d481b4b7b7",
                  "title": "An Introduction to Information Retrieval",
                  "type": "patent",
                  "authors": [
                            {
                                        "first_name": "Christopher D.",
                                        "last_name": "Manning"
                                      },
                            {
                                        "first_name": "Prabhakar",
                                        "last_name": "Raghavan"
                                      }
                          ],
                  "year": 2009,
                  "source": "Online",
                  "identifiers": {
                            "issn": "13864564",
                            "doi": "10.1109/LPT.2009.2020494",
                            "pmid": "10575050",
                            "arxiv": "0521865719 9780521865715",
                            "isbn": "0521865719"
                          },
                  "keywords": [
                            "keyword"
                          ],
                  "created": "2015-02-13T18:17:48.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-17T15:27:14.000Z",
                  "abstract": "Class-tested and coherent, this groundbreaking new textbook teaches web-era information retrieval, including web search and the related areas of text classification and text clustering from basic concepts. Written from a computer science perspective by three leading experts in the field, it gives an up-to-date treatment of all aspects of the design and implementation of systems for gathering, indexing, and searching documents; methods for evaluating systems; and an introduction to the use of machine learning methods on text collections. All the important ideas are explained using examples and figures, making it perfect for introductory courses in information retrieval for advanced undergraduates and graduate students in computer science. Based on feedback from extensive classroom experience, the book has been carefully structured in order to make teaching more natural and effective. Although originally designed as the primary text for a graduate or advanced undergraduate course in information retrieval, the book will also create a buzz for researchers and professionals alike."
                },
          {
                  "id": "de25a64f-493b-330e-a48c-4089bab938f5",
                  "title": "Learning of ontologies for the web: The analysis of existent approaches",
                  "type": "journal",
                  "authors": [
                            {
                                        "first_name": "Borys",
                                        "last_name": "Omelayenko"
                                      }
                          ],
                  "year": 2001,
                  "source": "CEUR Workshop Proceedings",
                  "identifiers": {
                            "issn": "16130073"
                          },
                  "created": "2015-02-13T18:17:52.000Z",
                  "profile_id": "53f383b4-1100-30d5-9473-2dde614dfcaa",
                  "last_modified": "2015-02-13T20:34:43.000Z",
                  "abstract": "The next generation of the Web, called Semantic Web, has to improve\\nthe Web with semantic (ontological) page annotations to enable knowledge-level\\nquerying and searches. Manual construction of these ontologies will\\nrequire tremendous efforts that force future integration of machine\\nlearning with knowledge acquisition to enable highly automated ontology\\nlearning. In the paper we present the state of the-art in the field\\nof ontology learning from the Web to see how it can contribute to\\nthe task..."
                }
        ]
}

mock_responses = {k:dumps(v) for k,v in mock_responses.iteritems()}

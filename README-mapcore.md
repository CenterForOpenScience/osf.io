# NII GRDM - mAP core連携機能

mAP coreは学認クラウドゲートウェイサービスのグループ管理機能を、APIを通して提供する。
ユーザーごとにOAuthによる認証を経て得られるAccessTokenを用いてmAP coreのAPI利用する。

GRDMのmAP core連携機能は、GRDMの各ProjectとそのContributorsを、mAP(クラウドゲートウェイ)のグループとそのメンバーに、自動的に双方向に同期する機能である。

本文書では、mAP core連携機能を利用するための設定方法などを解説する。

## 設定方法

mAP core連携機能を有効化するために、設定ファイルに記入するパラメータを以下に示す。

### website/settings/local.py ファイル

以下の設定を追加する。

* MAPCORE_HOSTNAME
mAP coreサーバーのURLを示す。httpsからホストのFQDNまでを記入する。末尾のスラッシュは不要。デフォルトは https://sptest.cg.gakunin.jp
本項目が未設定の場合は、mAP core連携機能自体が無効化される。
* MAPCORE_AUTHCODE_PATH
mAP coreから Authorization Codeを入手するAPIエンドポイントを指定する。デフォルトは /oauth/shib/authrequest.php
* MAPCORE_TOKEN_PATH
mAP coreから Access Tokenなどを入手するAPIエンドポイントを指定する。デフォルトは /oauth/token.php
* MAPCORE_REFRESH_PATH
mAP coreにて Access Token / Refresh Tokenの更新を行うAPIエンドポイントを指定する。デフォルトは /oauth/token.php
* MAPCORE_API_PATH  
mAP coreのグループ/メンバー操作を行うAPIのエンドポイントを指定する。デフォルトは /api2/v1  
* MAPCORE_AUTHCODE_MAGIC
OAuth2認証におけるstateフィールドの値(任意の文字列)を指定する。デフォルトは GRDM_mAP_AuthCode
* MAPCORE_CLIENTID
mAP coreのClient IDを指定する。デフォルトは未設定(本機能無効)。
* MAPCORE_SECRET
Client IDとペアになるシークレットキーを指定する。デフォルトは未設定。


## Client IDの取得

ユーザごとのAccess Tokenの発行・管理をGRDMからおこなうためには、
Client IDとSecretをGRDMホストに設定する必要がある。

### クラウドゲートウェイ利用申請

クラウドゲートウェイ管理者に以下を申請する。

* SPコネクタの作成とSPコネクタ管理者を追加
* 対象SP(このSPコネクタを利用するSP)にcasコンテナのentityIDを登録


### 必要な情報

mAP coreのためのClient IDとSecretの発行するには、以下の情報が必要となる。

1. GRDM casコンテナ(accountsホスト)用のTLS証明書とその秘密鍵
Client IDの自動発行サービスでは、Shibbolethに登録されているホスト証明書を、TLSクライアント認証用に使用する
1. Shibbolethの entityID (GRDM casコンテナのURI + /shibboleth-sp)
1. Redirect URI
OAuth認証が完了して後に、mAP coreからAccess Tokenなどを受け取るためのエンドポイントのURI。
本システムの場合は、`https://GRDM serverコンテナ(wwwホスト)のホスト名/mapcore_oauth_complete`となる

### 取得手順

mAP coreに宛てて以下のリクエストを投げる。

1. mAP coreサーバのエンドポイント `/oauth/sslauth/issue.php`に宛てて
1. TLSクライアント認証用の証明書と鍵を添えて
1. 次のパラメータを含むGETリクエスト
  `entytyid=<shibbolethのentityID>`
  `redirect_uri=<Redirect URI>`

curlコマンドの場合は、以下のように実行する。

`$ curl -k --key <TLS_KEY_FILE> --cert <TLS_CERT_FILE> "https://<mAP coreサーバのFQDN>/oauth/sslauth/issue.php?entityid=<ShibbolethのEntityID>&redirect_uri=<REDIRECT>"`

以下は実行例。

`curl -k --key rdm-accounts-privkey.pem --cert rdm-accounts-cert.pem "https://sptest.cg.gakunin.jp/oauth/sslauth/issue.php?entityid=https://accounts.dev1.rdm.nii.ac.jp/shibboleth-sp&redirect_uri=https://www.dev1.rdm.nii.ac.jp/mapcore_oauth_complete"`

成功すると、JSON形式でClient IDとSecretが返される。

    {"client_id":"abcdefghijklmnop","client_secret":"0123456889abcdefghijklmnopqrstuv"}

これらの値を、MAPCORE_CLIENTID, MAPCORE_SECRET に記入する。以下は例。

    MAPCORE_CLIENTID=abcdefghijklmnop
    MAPCORE_SECRET=0123456889abcdefghijklmnopqrstuv

## 各ユーザー利用手順概要

* クラウドゲートウェイにアカウントを作成しておく。(IdPでログインする)
* GRDMにログインする。 (同一IdPでログインする)
* mAP coreとアカウントの同期が必要な案内画面が表示される。(初回のみ)
* mAP core Authorization Service 画面に遷移する。(同一IdPでログインしてから)
* GRDMとmAP coreアカウントの紐付けに同意する。
* GRDMの画面に遷移する。

## 注意事項

* 各GRDMプロジェクト(=mAPグループ)の管理者は、グループ情報やメンバーの所属や権限変更操作をクラウドゲートウェイ上でおこなうか、GRDM上でおこなうか、どちらか一方で操作すると決めておくこと。
  * GRDMを正として操作することを強く推奨する。
  * GRDM管理者がmapcore_configコマンドにより同期を無効化した場合、再度有効化した場合にmapcore_upload_allコマンドで強制的に同期可能だが、その際クラウドゲートウェイ側での変更が失われるため。
  * GRDMとクラウドゲートウェイで同時に同じグループの状態を変更した場合の動作は不定となる。
  * GRDM上でのグループ情報とメンバー変更操作は、その都度、クラウドゲートウェイ側にも反映される。
  * クラウドゲートウェイ上での変更は即座にGRDM側に反映されず、GRDMの所属プロジェクト一覧画面や、各プロジェクトの画面にアクセスするとGRDM側に反映される。
  * クラウドゲートウェイ上での操作の結果、グループの状態を変更できるメンバーが居なくなった場合、同期することができない。例えば、クラウドゲートウェイ側で全メンバー入れ替えをおこなうと、そのグループにアクセスできるGRDMユーザーが居ないため、同期不能となる。

* 各プロジェクトの管理者は、定期的にGRDMプロジェクトにアクセスしたほうが良い。
** プロジェクト一般メンバー(Contributor)でGRDMにアクセスする際、プロジェクト管理者の権限でmAP coreにAPIを発行することがあるため、プロジェクト管理者のアクセストークンが無効の場合に、一般メンバーが操作不能になることがある。

* GRDM側でプロジェクト更新時は、mAP側へ状態を反映する。

* 通常、GRDMプロジェクト読み込み時は、mAP側の状態をGRDMに反映する。しかし、GRDM側のプロジェクトを変更した際に、mAP側への反映がエラーになった場合、次回プロジェクト画面読み込み時にmAP側へ反映しようとする。それが成功するまでは、アクセスするたびにGRDM側を主として反映しようとリトライするため、GRDM側を主として情報を変更したほうが良い。(その間のmAP側グループ状態の変更は破棄される。)

* クラウドゲートウェイで一般(管理者ではない)メンバーとして設定変更された場合、GRDM側ではRead+WriteのPermissionsとなる。GRDM側でReadのPermissionsに変えた場合は、クラウドゲートウェイ側では一般メンバーのままとなる。

* GRDM は自動的にmAP core API利用のリフレッシュトークンを更新し、各ユーザーがクラウドゲートウェイへのログインとAPI利用の同意をおこなう頻度を減らしている。しかし、その自動更新が停止した場合、またはリフレッシュトークン自動更新が長時間失敗した場合に、各ユーザーはクラウドゲートウェイへの再ログインと同意が必要になる。

## mAP core連携機能管理ツール

以下のコマンドを server コンテナのシェル上で実行できる。

### mAP core連携機能の無効化・有効化

GRDMのサーバーを停止せずにmAP core連携機能を無効化・有効化できる。

```
# cd /code
# inv -h mapcore_config
Usage: inv[oke] [--core-opts] mapcore_config [--options] [other tasks here ...]

Docstring:
  mAP core configurations

  Examples:
        inv mapcore_config --sync=yes
	      inv mapcore_config --sync=no

Options:
  -s STRING, --sync=STRING
```

このコマンドで変更した状態はデータベース (Django, PostgreSQL) に保存さ
れる。

オプション--syncにnoを指定し、mAP core連携機能を停止すると、GRDMプロジェ
クトとmAP側のグループは同期されなくなる。

同期されていない状態でGRDM側のプロジェクト名などを変更した場合、オプショ
ン--syncをyesに戻しても同期されず、その状態のまま利用を続けると、通常
はmAP側が正となって動作するため、変更が戻ってしまうことになる。

そのため、オプション--syncをyesに戻した直後に、すべてのGRDMプロジェク
トを正として一旦同期するためには mapcore_upload_all コマンドを使用する
必要がある。

### mAP core連携機能: GRDM側を主として強制的にすべてのプロジェクトを同期

```
# inv -h mapcore_upload_all
Usage: inv[oke] [--core-opts] mapcore_upload_all [other tasks here ...]

Docstring:
  Synchronize all GRDM projects to mAP core

Options:
  none
```

mapcore_config コマンドにおいて、オプション--syncをnoにしていた場合は、
このコマンドを実行しても同期しない。その場合、コマンド終了ステータスは
0以外を返す。

同期の際、エラーになったプロジェクトが一つ以上存在した場合は、このコマ
ンド終了ステータスは0以外を返す。

同期を無効にしていた場合に、クラウドゲートウェイ側でグループの名前、説
明、メンバーを変更すると、再度同期を有効にしたあとにこのコマンドを実行
すると、それらの変更は失われる。


### OAuthアクセストークンの消去

```
# cd /code
# inv -h mapcore_remove_token
Usage: inv[oke] [--core-opts] mapcore_remove_token [--options] [other tasks here ...]

Docstring:
    Remove OAuth token for mAP core

Options:
  -e STRING, --eppn=STRING
  -u STRING, --username=STRING
```

### GRDMプロジェクト・mAPグループ削除コマンド

開発用、または連携するmAP(CloudGateway)を変更する場合を想定したコマン
ド。各プロジェクトの group key をクリアすれば、再度mAP側グループを作成
し、連携しなおすことができる。

```
# cd /code
# inv -h mapcore_rmgroups
Usage: inv[oke] [--core-opts] mapcore_rmgroups [--options] [other tasks here ...]

Docstring:
  GRDM/mAP group maintanance utility for bulk deletion

Options:
  -d, --dry-run              dry-run
  -f STRING, --file=STRING   file name contains group_key list
  -g, --grdm                 remove groups from GRDM
  -i, --interactive          select delete groups interactively
  -k, --key-only             remove link (group_key) only
  -m, --map                  remove groups from mAP
  -u STRING, --user=STRING   filter with creator's mail address
  -v, --verbose              show more group information
```

### ユーザーとプロジェクトごとのロック用フラグをクリア

通常は操作不要。(finally節でアンロックしているため。)
異常終了した場合にロックされたままになる可能性があるため。
(主に開発用)

```
Usage: inv[oke] [--core-opts] mapcore_unlock_all [other tasks here ...]

Docstring:
  Remove all lock flags for mAP core

Options:
   none
```

### mAP core API操作用ロック処理のテスト

mAP core API操作用のロック機構が機能しているかどうか確認する。

```
Usage: inv[oke] [--core-opts] mapcore_test_lock [other tasks here ...]
```

複数プロセスで同時にsleep処理をロックしてから実行する。もし、ロック機
構が効かない場合、並列に実行できてしまい、期待する実行時間よりも短くな
ることで、エラーを検出する。
エラーの場合は「ERROR: mapcore_test_lock」が表示される。

test_mapcore.py などのテストにはマルチプロセスによる並列実行のテストを
実装できないため、このテスト実行方法を用意した。

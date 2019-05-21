# NII GRDM - mAP core連携機能

mAP coreは学認クラウドゲートウェイサービスのグループ管理機能を、APIを通して提供する。
OAuthによる認証を経て得られるAccessTokenを用いてmAP coreのAPI利用する。

GRDMのmAP core連携機能は、GRDMのProjectとそのContributorsを、mAP(クラウドゲートウェイ)のグループとそのメンバーに、自動的に双方向に同期する機能である。

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

mAP core APIを使用するためには、ユーザ毎にOAuth2による認証を経て発行される Access Tokenが必要となる。
ユーザ毎のAccess Tokenの発行・管理をGRDMからおこなうためには、
Client IDとSecretをGRDMホストに設定する。

### クラウドゲートウェイ利用申請

クラウドゲートウェイ管理者に以下を申請する。

* SPコネクタの作成とSPコネクタ管理者を追加
* 対象SP(このSPコネクタを利用するSP)にcasコンテナのentityIDを登録


### 必要な情報

mAP coreからClient IDとSecretの発行するには、以下の情報が必要となる。

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
* GRDMにログインする。 (IdPでログインする)
* 自動的にクラウドゲートウェイ画面に遷移する。(一度だけ)
* クラウドゲートウェイにログインする。 (IdPでログインする)
* mAp core Authorization Service に遷移する。
* GRDMとmAP coreアカウントの紐付けに同意する。
* GRDMの画面に戻る。

## 注意事項

* プロジェクト(グループ)管理者は、グループとメンバーの変更操作をクラウ  ドゲートウェイでおこなうか、GRDMでおこなうか、どちらか一方で操作すること。
  * GRDMとクラウドゲートウェイで同時に同じグループを変更した場合の動作は不定となる。

* クラウドゲートウェイで設定された一般(管理者ではない)メンバーは、GRDM側ではRead+WriteのPermissionsとなる。GRDM側でReadのPermissionsに変えた場合は、クラウドゲートウェイ側では一般メンバーのままとなる。

* GRDM は自動的にmAP core API利用のリフレッシュトークンを更新することで、各ユーザーがクラウドゲートウェイへログインと同意をおこなう頻度を減らしている。しかし、その更新が停止した場合、またはリフレッシュトークン自動更新が失敗した場合に、再ログインと同意が必要になる。

# NII GRDM  - mAP core 連携機能

mAP coreは、Cloud Gatewayの持つグループ管理機能を、APIを通して提供するものである。
一般的なOAuthによる認証を経て得られるAccessTokenを用いて、APIを発行して利用する仕組みとなっている。

GRDMのmAP core連携機能は、GRDMのProjectとそのContributorを、mAP(クラウドゲートウェイ)のグループとそのメンバーに、
自動的に双方向に同期する機能である。本文書では、GRDMに組み込まれたこの機能を利用するための設定方法などを解説する。

## 設定方法

mAP core連携機能を有効化するために、設定ファイルに記入するパラメータを以下に示す。

### osf.env ファイル

* MAPCORE_HOSTNAME  
mAP coreサーバーのURLを示す。httpsからホストのFQDNまでを記入する。末尾のスラッシュは不要。
本項目が未設定の場合は、mAP core連携機能自体が無効化される
* MAPCORE_AUTHCODE_PATH  
mAP coreから Authorization Codeを入手するAPIエンドポイントを指定する。デフォルトでは`/oauth/shib/authrequest.php`
* MAPCORE_TOKEN_PATH  
mAP coreから Access Tokenなどを入手するAPIエンドポイントを指定する。デフォルトでは`/oauth/token.php`
* MAPCORE_REFRESH_PATH
mAP coreにて Access Token / Refresh Tokenの更新を行うAPIエンドポイントを指定する。デフォルトでは`/oauth/token.php`
* MAPCORE_API_PATH  
mAP coreのグループ/メンバー操作を行うAPIのエンドポイントを指定する。デフォルトでは`/api2/v1`  
* MAPCORE_AUTHCODE_MAGIC=GRDM_mAP_AuthCode
OAuth2認証におけるstateフィールドのデフォルト値を指定する。任意の文字列

### osf-secret.env ファイル

* MAPCORE_CLIENTID  
mAP coreを利用するために、クライアントホスト毎に発行される Client IDを指定する
* MAPCORE_SECRET  
Client IDとペアになるシークレットキーを指定する


## Client IDの取得

mAP core APIを使用するためには、ユーザ毎にOAuth2による認証を経て発行される Access Tokenが必要となる。
ユーザ毎のAccess Tokenの発行・管理はGRDMによって自動化されているが、ホスト毎に発行される Client IDと Secretが必要となる。

### 必要な情報

mAP coreでは、この Client IDと Secretの発行も自動化されているが、その際に以下の情報が必要となるので、あらかじめ用意しておく。

1. GRDMホスト(account)のTLS証明書とその秘密鍵  
Client IDの自動発行サービスでは、Shibbolethに登録されているホスト証明書を、TLSクライアント認証用に使用する
1. Shibbolethの EntityID
1. Redirect URI  
OAuth認証が完了して後に、mAP coreからAccess Tokenなどを受け取るためのエンドポイントのURI。
本システムの場合は、`https://Webサーバのホスト名/mapcore_oauth_complete`となる

### 取得手順

mAP coreに宛てて以下のリクエストを投げる。

1. mAP coreサーバのエンドポイント `/oauth/sslauth/issue.php`に宛てて
1. TLSクライアント認証用の証明書と鍵を添えて
1. 次のパラメータを含むGETリクエスト  
  `entytyid=<shibbolethのEntityID>`  
  `redirect_uri=<Redirect URI>`

curlコマンドの場合は、以下のようになる。

`$ curl -k --key <TLS_KEY_FILE> --cert <TLS_CERT_FILE> "https://<mAP coreサーバのFQDN>/oauth/sslauth/issue.php?entityid=<ShibbolethのEntityID>&redirect_uri=<REDIRECT>"`

リクエスト正常に受け付けられると、JSON形式で Client IDと対応する Secretが返される。

    {"client_id":"ccf28ddd6d74653c","client_secret":"3c2946308f2bb328dae3d8260995d581"}

これらの値を、osf-secret.envファイルに記入する。

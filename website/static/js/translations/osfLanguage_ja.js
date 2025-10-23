var $osf = require('js/osfHelpers');

module.exports = {
    REFRESH_OR_SUPPORT: $osf.refreshOrSupport(),
    SUPPORT_LINK: $osf.osfSupportLink(),
    // TODO
    makePublic: null,
    makePrivate: null,
    registrations: {
        registrationFailed: '登録に失敗しました。 この問題が解決しない場合は、' + $osf.osfSupportEmail() + 'までご連絡ください。' ,
        invalidEmbargoTitle: '無効な禁止終了日',
        invalidEmbargoMessage: '今日から2日以上4年未満の日付を選択してください。',
        registerConfirm: '続行する前に...',
        registerSkipAddons: 'この時点で登録を続行することを選択した場合、コピーできないアドオンのコンテンツは除外されます。 これらのファイルは、最終登録には表示されません。',
        registerFail: '登録の完了中に問題が発生しました。 後でもう一度やり直してください。 これが発生するはずがなく、問題が解決しない場合は、' + $osf.osfSupportLink() + 'に報告してください。',
        submitForReviewFail: '現在、このドラフトをレビュー用に送信中に問題が発生しました。 後でもう一度やり直してください。 これが発生するはずがなく、問題が解決しない場合は、' + $osf.osfSupportLink() + 'に報告してください。',
        beforeEditIsApproved: 'このドラフト登録は現在承認されています。 変更（コメントを除く）を行うと、この承認ステータスは取り消され、再度承認を受けるために送信する必要があることに注意してください。',
        beforeEditIsPendingReview: 'このドラフト登録は現在審査中です。 変更（コメントを除く）を行うと、このリクエストはキャンセルされ、再度承認を受けるために送信する必要があります。',
    },
    Addons: {
        dataverse: {
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
            confirmUserDeauth: 'Dataverseアカウントのリンクを解除してもよろしいですか？' +
                'これにより、承認したすべてのプロジェクトのDataverseへの' +
                ' アクセスが取り消されます。',
            confirmNodeDeauth: 'このDataverseアカウントのリンクを解除してもよろしいですか？ これにより、' +
                'GakuNin RDMからDataverseの調査のファイルを表示、ダウンロード、変更、およびアップロードする機能が' +
                '無効になります。 これにより、' +
                '<a href="/settings/addons/">ユーザー設定</a>ページからDataverse認証が削除されることはありません。 ' ,
            deauthError: '現在、Dataverseアカウントを切断できませんでした。',
            deauthSuccess: 'Dataverseアカウントの切断と接続に成功しました。',
            authError: '申し訳ありませんが、Dataverseのそのインスタンスへの接続に問題がありました。' +
                'インスタンスがDataverse 4.0にアップグレードされていない可能性があります。' +
                'ご質問がある場合、またはこれがエラーだと思われる場合は、' + $osf.osfSupportEmail() + 'お問い合わせください。' ,
            authInvalid: 'Dataverse APIトークンが無効です。',
            authSuccess: 'Dataverseアカウントがリンクされました。',
            datasetDeaccessioned: 'このデータセットは既にDataverseでアクセス解除されており、' +
                'GakuNin RDMに接続できません。',
            forbiddenCharacters: 'このデータセットは、1つ以上のデータセットのファイル名に' +
                '使用できない文字があるため、接続できません。 この問題は開発チームに' +
                '転送されました。',
            setDatasetError: 'このデータセットに接続できませんでした。',
            widgetInvalid: 'このDataverseアカウントに関連付けられた資格情報は' +
                '無効のようです。',
            widgetError: 'Dataverseへの接続に問題がありました。'
        },
        dropbox: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: '本当にDropboxアカウントを切断しますか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのDropboxへの' +
                'アクセスが取り消されます。',
            deauthError: '現時点ではDropboxアカウントを切断できませんでした',
        },
        figshare: {
            confirmDeauth: 'figshareアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けられているすべてのプロジェクトのfigshareへの' +
                'アクセスが取り消されます。',
        },
        github: {
            confirmDeauth: 'GitHubアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのGitHubへの' +
                'アクセスが取り消されます。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        bitbucket: {
            confirmDeauth: 'Bitbucketアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのBitbucketへの' +
                'アクセスが取り消されます。',
        },
        gitlab: {
            confirmDeauth: 'GitLabアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのGitLabへの' +
                'アクセスが取り消されます。',
        },
        s3:{
            authError: '現在、Amazon S3に接続できませんでした。 後でもう一度やり直してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は、' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Googleドライブアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのGoogleドライブへの' +
                'アクセスが取り消されます。',
            deauthError: '現在、Googleドライブアカウントを切断できませんでした',
        },
        onedrive: {
            // Shown on clicking "Delete Access Token" for onedrive
            confirmDeauth: 'Microsoft OneDriveアカウントを切断してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのMicrosoft OneDriveへの' +
                'アクセスが取り消されます。',
            deauthError: '現在、Microsoft OneDriveアカウントを切断できませんでした',
        },
        owncloud: {
            authError: '無効なownCloudサーバー',
            authInvalid: '無効な資格情報。 有効なユーザー名とパスワードを入力してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。' ,
            confirmAuth : 'ownCloud認証情報でこのプロジェクトを承認してもよろしいですか？',
            updateAccountsError : '現在、ownCloudアカウントリストを取得できませんでした。' +
                        'ページを更新してください。 問題が解決しない場合は、こちらにメールをして下さい：' +
                        $osf.osfSupportLink(),
            submitSettingsSuccess : 'フォルダーが正常にリンクされました',
        },
        swift: {
            authError: '現在、OpenStack Swiftに接続できませんでした。 後でもう一度やり直してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        azureblobstorage: {
            authError: '現在、Azure Blob Storageに接続できませんでした。 後でもう一度やり直してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        weko: {
            authError: '現在、JAIRO Cloudに接続できませんでした。 後でもう一度やり直してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        s3compat: {
            authError: '現在、S3互換ストレージに接続できませんでした。 後でもう一度やり直してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        nextcloud: {
            authError: '無効なNextcloudサーバー',
            authInvalid: '無効な資格情報。 有効なユーザー名とパスワードを入力してください。',
            userSettingsError: '設定を取得できませんでした。 ページを更新するか、' +
                '問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        },
        iqbrims: {
            // Shown on clicking "Delete Access Token" for iqbrims
            confirmDeauth: 'IQB-RIMSアカウントの接続を解除してもよろしいですか？' +
                'これにより、このアカウントに関連付けたすべてのプロジェクトのIQB-RIMSへのアクセスが取り消されます。',
            deauthError: '現在、IQB-RIMSアカウントを切断できませんでした',
            depositHelp: '論文を登録して承認を申請する',
            checkHelp: '論文を提出する前に画像のみのスキャンサービスを実行する',
            labo: '研究分野',
            accepted_date: '受理日',
            journal_name: '雑誌名',
            doi: 'DOI',
            publish_date: '出版日',
            volume: '巻（号）',
            page_number: 'ページ番号',
            workflow_overall_state: '審査状況'
        },
    },
    apiOauth2Application: {
        discardUnchanged: '保存していない変更を破棄してもよろしいですか？',
        deactivateConfirm: 'すべてのユーザーに対してこのアプリケーションを無効にし、すべてのアクセストークンを取り消してもよろしいですか？ これを元に戻すことはできません。',
        deactivateError: 'アプリケーションを無効にできませんでした。 数分待ってからもう一度試すか、問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        dataFetchError: 'データがロードされていません。' + $osf.refreshOrSupport(),
        dataListFetchError: '現在、開発者アプリケーションのリストを読み込めませんでした。' + $osf.refreshOrSupport(),
        dataSendError: 'サーバーへのデータ送信エラー。 すべてのフィールドが有効であることを確認するか、問題が解決しない場合は'+ $osf.osfSupportLink() + 'へお問い合わせください。' ,
        creationSuccess: '新規アプリケーションが正常に登録されました',
        dataUpdated: '更新されたアプリケーションデータ',
        resetSecretConfirm: 'クライアントシークレットをリセットしてもよろしいですか？ これを元に戻すことはできません。 アプリケーションは、新しいクライアントシークレットで更新されるまで使用できなくなり、すべてのユーザーがアクセスを再承認する必要があります。 以前に発行されたアクセストークンは機能しなくなります。',
        resetSecretError: 'クライアントシークレットをリセットできませんでした。 数分待ってからもう一度試すか、問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
    },
    apiOauth2Token: {
        discardUnchanged: '保存していない変更を破棄してもよろしいですか？',
        deactivateConfirm: 'このトークンを無効にしますか？ これを元に戻すことはできません。',
        deactivateError: 'トークンを無効にできませんでした。 数分待ってからもう一度試すか、問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。' ,
        dataFetchError: 'データがロードされていません。' + $osf.refreshOrSupport(),
        dataListFetchError: 'Could not load list of personal access tokens at this time. ' + $osf.refreshOrSupport(),
        dataSendError: 'サーバーへのデータ送信エラー：すべてのフィールドが有効であることを確認するか、問題が解決しない場合は' + $osf.osfSupportLink() + 'へお問い合わせください。',
        creationSuccess: '新しい個人用アクセストークンが正常に生成されました。 このトークンは期限切れになりません。 このトークンを他の人と共有しないでください。 誤って公開された場合は、すぐに無効にする必要があります。',
        dataUpdated: 'トークンデータが更新されました'
    },
    projectSettings: {
        updateSuccessMessage: 'プロジェクトの設定を更新しました。',
        updateErrorMessage400: 'プロジェクト設定の更新エラーです。 すべてのフィールドが有効であることを確認してください。',
        updateErrorMessage: 'プロジェクト設定を更新できませんでした。' + $osf.refreshOrSupport(),
        instantiationErrorMessage: '更新URLなしでProjectSettingsビューモデルをインスタンス化しようとしています'
    }
};

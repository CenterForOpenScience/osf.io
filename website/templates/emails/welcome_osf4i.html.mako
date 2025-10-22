<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">GakuNin RDMにようこそ！</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">

こんにちは、${user.fullname}さん<br>
<br>
GakuNin RDMアカウントを認証していただきありがとうございます。GakuNin RDMは国立情報学研究所が提供のオープンソースサービスです。GakuNin RDMの機能の一部をご紹介します：
<br>

% if storage_flag_is_active:
<h4>ストレージの場所の指定</h4>
新しいプロジェクトのファイルの保存場所は、選択肢にある地域の中からお選びいただけます。 <a href="${domain}settings/account/?utm_source=notification&utm_medium=email&utm_campaign=welcome#updateDefaultStorageLocation">ストレージの場所を指定</a>。<br>
<br>
% endif

<h4>ファイルの保存</h4>
資料、データ、原稿など、研究に関連するデータを全て研究途中あるいは完了後にアーカイブ化できます。 <a href="https://support.rdm.nii.ac.jp/usermanual/23/">やり方を見る</a>。<br>
<br>

<h4>研究機関とプロジェクトを関連付け</h4>
プロジェクトをあなたの所属研究機関と関連付けましょう。研究機関で業績が取り上げられることで人目に触れやすくなり、共同研究が促進されます。<br>
<br>

% if use_viewonlylinks:
<h4>研究内容の共有</h4>
研究資料を非公開で管理、特定ユーザとの限定共有をすることができます。共同研究者を追加すれば研究資料やデータなどの保管環境を共有でき、ファイルが行方不明になるのを防げます。<a href="https://support.rdm.nii.ac.jp/usermanual/14/">プライバシー設定について詳しく</a>。<br>
<br>
% endif
<!--
<h4>研究の登録</h4>
プロジェクトやファイルはタイムスタンプ付きの永久ファイルとして保存できます。こうすることで検証的試験を行う際の研究デザインと分析プランを事前登録できるほか、報告書を出版する際に資料やデータ、分析結果をアーカイブ化できます。<a href="https://openscience.zendesk.com/hc/en-us/articles/360019930893/?utm_source=notification&utm_medium=email&utm_campaign=welcome">登録について見る</a>。<br>
<br>

<h4>研究を引用可能に</h4>
GakuNin RDM上のプロジェクトは全て固有の永続的識別子がついており、登録には全てデジタルオブジェクト識別子を割り振ることができます。公開プロジェクトの引用は自動生成されるので、訪問者が典拠を表示することができます。<a href="https://openscience.zendesk.com/hc/en-us/articles/360019931013/?utm_source=notification&utm_medium=email&utm_campaign=welcome">もっと詳しく</a>。<br>
<br>

<h4>インパクトの測定</h4>
公開プロジェクトへのトラフィックや公開ファイルのダウンロード数をモニタリングできます。 <a href="https://openscience.zendesk.com/hc/en-us/articles/360019737874/?utm_source=notification&utm_medium=email&utm_campaign=welcome">アナリティクスについて詳しく</a>。<br>
<br>
-->
<h4>使用中のサービスと接続</h4>
GakuNin RDMはAmazon S3、Azure Blob Storage、Bitbucket、Box、Dataverse、Dropbox、figshare、GitHub、GitLab、Google Drive、Mendeley、Nextcloud、OneDrive、OpenStack Swift、ownCloud、S3 Compatible Storage、JAIRO Cloud、Zoteroとの統合が可能。各種サービスをGakunin RDMプロジェクトとリンクすれば、研究資料を全て1か所にまとめられます。<a href="https://support.rdm.nii.ac.jp/usermanual/24/">アドオンについて詳しく見る</a>。<br>
<br>

Gakunin RDMについての詳細は<a href="https://support.rdm.nii.ac.jp/">サポート</a>をご覧ください。<br>
<br>
よろしくお願いいたします。<br>
<br>
国立情報学研究所チーム<br>

  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Welcome to the GakuNin RDM!</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">

Hello ${user.fullname},<br>
<br>
Thank you for verifying your account on GakuNin RDM, a free, open source service maintained by the National Institute of Informatics. Here are a few things you can do with GakuNin RDM:
<br>

% if storage_flag_is_active:
<h4>Select your storage location</h4>
Files can be stored in a location you specify from the available geographic regions for new projects. <a href="${domain}settings/account/?utm_source=notification&utm_medium=email&utm_campaign=welcome#updateDefaultStorageLocation">Set storage location.</a><br>
<br>
% endif

<h4>Store your files</h4>
Archive your materials, data, manuscripts, or anything else associated with your work during the research process or after it is complete. <a href="https://support.rdm.nii.ac.jp/usermanual/23/">Learn how.</a><br>
<br>

<h4>Affiliate your projects with your institution</h4>
Associate your projects with your institution. They will be added to your institution's central commons, improving discoverability of your work and fostering collaboration.<br>
<br>

% if use_viewonlylinks:
<h4>Share your work</h4>
Keep your research materials and data private, make it accessible to specific others with view-only links, or make it publicly accessible. You have full control of what parts of your research are public and what remains private.Add your collaborators to have a shared environment for maintaining your research materials and data and never lose files again. <a href="https://support.rdm.nii.ac.jp/usermanual/14/">Explore privacy settings.</a><br>
<br>
% endif
<!--
<h4>Register your research</h4>
Create a permanent, time-stamped version of your projects and files.  Do this to preregister your design and analysis plan to conduct a confirmatory study, or archive your materials, data, and analysis scripts when publishing a report. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019930893/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Read about registrations.</a><br>
<br>

<h4>Make your work citable</h4>
Every project and file on the GakuNin RDM has a permanent unique identifier, and every registration can be assigned a DOI.  Citations for public projects are generated automatically so that visitors can give you credit for your research. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019931013/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Learn more.</a><br>
<br>

<h4>Measure your impact</h4>
You can monitor traffic to your public projects and downloads of your public files. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019737874/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Discover analytics.</a><br>
<br>
-->
<h4>Connect services that you use</h4>
GakuNin RDM integrates with GitHub, Dropbox, Google Drive, Box, Dataverse, figshare, Amazon S3, ownCloud, Bitbucket, GitLab, OneDrive, Mendeley, and Zotero. Link the services that you use to your GakuNin RDM projects so that all parts of your research are in one place <a href="https://support.rdm.nii.ac.jp/usermanual/24/">Learn about add-ons.</a><br>
<br>

Learn more about GakuNin RDM by reading the <a href="https://support.rdm.nii.ac.jp/">Guides</a>.<br>
<br>
Sincerely,<br>
<br>
The National Institute of Informatics Team<br>

  </td>
</tr>
</%def>

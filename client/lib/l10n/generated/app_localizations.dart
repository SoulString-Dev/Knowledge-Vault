import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('zh')];

  /// No description provided for @appTitle.
  ///
  /// In zh, this message translates to:
  /// **'知识匣'**
  String get appTitle;

  /// No description provided for @serverAddress.
  ///
  /// In zh, this message translates to:
  /// **'服务器地址'**
  String get serverAddress;

  /// No description provided for @serverAddressHint.
  ///
  /// In zh, this message translates to:
  /// **'https://your-server.com'**
  String get serverAddressHint;

  /// No description provided for @username.
  ///
  /// In zh, this message translates to:
  /// **'用户名'**
  String get username;

  /// No description provided for @password.
  ///
  /// In zh, this message translates to:
  /// **'密码'**
  String get password;

  /// No description provided for @inviteCode.
  ///
  /// In zh, this message translates to:
  /// **'邀请码（选填）'**
  String get inviteCode;

  /// No description provided for @login.
  ///
  /// In zh, this message translates to:
  /// **'登录'**
  String get login;

  /// No description provided for @register.
  ///
  /// In zh, this message translates to:
  /// **'注册'**
  String get register;

  /// No description provided for @registerAccount.
  ///
  /// In zh, this message translates to:
  /// **'注册账号'**
  String get registerAccount;

  /// No description provided for @hasAccountGoLogin.
  ///
  /// In zh, this message translates to:
  /// **'已有账号？去登录'**
  String get hasAccountGoLogin;

  /// No description provided for @noAccountGoRegister.
  ///
  /// In zh, this message translates to:
  /// **'没有账号？去注册'**
  String get noAccountGoRegister;

  /// No description provided for @loginFailed.
  ///
  /// In zh, this message translates to:
  /// **'登录失败'**
  String get loginFailed;

  /// No description provided for @networkError.
  ///
  /// In zh, this message translates to:
  /// **'网络错误，请检查服务器地址'**
  String get networkError;

  /// No description provided for @homeTitle.
  ///
  /// In zh, this message translates to:
  /// **'知识流'**
  String get homeTitle;

  /// No description provided for @searchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索知识卡…'**
  String get searchHint;

  /// No description provided for @statusAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get statusAll;

  /// No description provided for @statusPending.
  ///
  /// In zh, this message translates to:
  /// **'排队中'**
  String get statusPending;

  /// No description provided for @statusProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get statusProcessing;

  /// No description provided for @statusReady.
  ///
  /// In zh, this message translates to:
  /// **'就绪'**
  String get statusReady;

  /// No description provided for @statusFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get statusFailed;

  /// No description provided for @emptyList.
  ///
  /// In zh, this message translates to:
  /// **'还没有知识卡，点右下角 + 添加'**
  String get emptyList;

  /// No description provided for @emptyListFiltered.
  ///
  /// In zh, this message translates to:
  /// **'当前筛选没有知识卡'**
  String get emptyListFiltered;

  /// No description provided for @loadMoreFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载更多失败'**
  String get loadMoreFailed;

  /// No description provided for @addTitle.
  ///
  /// In zh, this message translates to:
  /// **'添加知识卡'**
  String get addTitle;

  /// No description provided for @addUrlTab.
  ///
  /// In zh, this message translates to:
  /// **'网页 URL'**
  String get addUrlTab;

  /// No description provided for @addPasteTab.
  ///
  /// In zh, this message translates to:
  /// **'粘贴文本'**
  String get addPasteTab;

  /// No description provided for @addUrlLabel.
  ///
  /// In zh, this message translates to:
  /// **'网页地址'**
  String get addUrlLabel;

  /// No description provided for @addUrlHint.
  ///
  /// In zh, this message translates to:
  /// **'https://example.com/article'**
  String get addUrlHint;

  /// No description provided for @addPasteTitleLabel.
  ///
  /// In zh, this message translates to:
  /// **'标题（选填）'**
  String get addPasteTitleLabel;

  /// No description provided for @addPasteTextLabel.
  ///
  /// In zh, this message translates to:
  /// **'文本内容'**
  String get addPasteTextLabel;

  /// No description provided for @addPasteFromClipboard.
  ///
  /// In zh, this message translates to:
  /// **'从剪贴板粘贴'**
  String get addPasteFromClipboard;

  /// No description provided for @addSubmit.
  ///
  /// In zh, this message translates to:
  /// **'提交'**
  String get addSubmit;

  /// No description provided for @addSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'已加入处理队列'**
  String get addSubmitted;

  /// No description provided for @addClipboardFound.
  ///
  /// In zh, this message translates to:
  /// **'检测到剪贴板中的网址，已预填'**
  String get addClipboardFound;

  /// No description provided for @detailTitle.
  ///
  /// In zh, this message translates to:
  /// **'知识卡'**
  String get detailTitle;

  /// No description provided for @summary.
  ///
  /// In zh, this message translates to:
  /// **'摘要'**
  String get summary;

  /// No description provided for @tags.
  ///
  /// In zh, this message translates to:
  /// **'标签'**
  String get tags;

  /// No description provided for @noSummary.
  ///
  /// In zh, this message translates to:
  /// **'分析完成后显示摘要'**
  String get noSummary;

  /// No description provided for @processingHint.
  ///
  /// In zh, this message translates to:
  /// **'正在处理，稍候自动刷新…'**
  String get processingHint;

  /// No description provided for @failedHint.
  ///
  /// In zh, this message translates to:
  /// **'处理失败'**
  String get failedHint;

  /// No description provided for @retry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get retry;

  /// No description provided for @reanalyze.
  ///
  /// In zh, this message translates to:
  /// **'重新分析'**
  String get reanalyze;

  /// No description provided for @edit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get edit;

  /// No description provided for @editTitle.
  ///
  /// In zh, this message translates to:
  /// **'编辑标题'**
  String get editTitle;

  /// No description provided for @editSummary.
  ///
  /// In zh, this message translates to:
  /// **'编辑摘要'**
  String get editSummary;

  /// No description provided for @save.
  ///
  /// In zh, this message translates to:
  /// **'保存'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get cancel;

  /// No description provided for @delete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get delete;

  /// No description provided for @deleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定删除这张知识卡吗？批注与标签关联将一并删除。'**
  String get deleteConfirm;

  /// No description provided for @openSource.
  ///
  /// In zh, this message translates to:
  /// **'打开原文'**
  String get openSource;

  /// No description provided for @wordCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 字'**
  String wordCount(int count);

  /// No description provided for @searchTitle.
  ///
  /// In zh, this message translates to:
  /// **'搜索'**
  String get searchTitle;

  /// No description provided for @searchMode.
  ///
  /// In zh, this message translates to:
  /// **'检索模式'**
  String get searchMode;

  /// No description provided for @modeHybrid.
  ///
  /// In zh, this message translates to:
  /// **'混合'**
  String get modeHybrid;

  /// No description provided for @modeKeyword.
  ///
  /// In zh, this message translates to:
  /// **'关键词'**
  String get modeKeyword;

  /// No description provided for @modeSemantic.
  ///
  /// In zh, this message translates to:
  /// **'语义'**
  String get modeSemantic;

  /// No description provided for @filterTag.
  ///
  /// In zh, this message translates to:
  /// **'标签筛选'**
  String get filterTag;

  /// No description provided for @filterStatus.
  ///
  /// In zh, this message translates to:
  /// **'状态筛选'**
  String get filterStatus;

  /// No description provided for @noResults.
  ///
  /// In zh, this message translates to:
  /// **'没有找到相关知识卡'**
  String get noResults;

  /// No description provided for @searchFirst.
  ///
  /// In zh, this message translates to:
  /// **'输入关键词开始检索'**
  String get searchFirst;

  /// No description provided for @detailPlaceholder.
  ///
  /// In zh, this message translates to:
  /// **'选择左侧卡片查看详情'**
  String get detailPlaceholder;

  /// No description provided for @matchedKeyword.
  ///
  /// In zh, this message translates to:
  /// **'关键词'**
  String get matchedKeyword;

  /// No description provided for @matchedSemantic.
  ///
  /// In zh, this message translates to:
  /// **'语义'**
  String get matchedSemantic;

  /// No description provided for @tagsTitle.
  ///
  /// In zh, this message translates to:
  /// **'标签管理'**
  String get tagsTitle;

  /// No description provided for @tagCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 张卡片'**
  String tagCount(int count);

  /// No description provided for @renameTag.
  ///
  /// In zh, this message translates to:
  /// **'重命名'**
  String get renameTag;

  /// No description provided for @mergeTag.
  ///
  /// In zh, this message translates to:
  /// **'合并到…'**
  String get mergeTag;

  /// No description provided for @mergeTagInto.
  ///
  /// In zh, this message translates to:
  /// **'将「{name}」合并到'**
  String mergeTagInto(String name);

  /// No description provided for @mergeConfirm.
  ///
  /// In zh, this message translates to:
  /// **'合并'**
  String get mergeConfirm;

  /// No description provided for @deleteTagConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定删除该标签吗？卡片本身不受影响。'**
  String get deleteTagConfirm;

  /// No description provided for @noTags.
  ///
  /// In zh, this message translates to:
  /// **'还没有标签，采集几张卡片后自动生成'**
  String get noTags;

  /// No description provided for @settingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'设置'**
  String get settingsTitle;

  /// No description provided for @themeMode.
  ///
  /// In zh, this message translates to:
  /// **'外观'**
  String get themeMode;

  /// No description provided for @themeSystem.
  ///
  /// In zh, this message translates to:
  /// **'跟随系统'**
  String get themeSystem;

  /// No description provided for @themeLight.
  ///
  /// In zh, this message translates to:
  /// **'浅色'**
  String get themeLight;

  /// No description provided for @themeDark.
  ///
  /// In zh, this message translates to:
  /// **'深色'**
  String get themeDark;

  /// No description provided for @logout.
  ///
  /// In zh, this message translates to:
  /// **'退出登录'**
  String get logout;

  /// No description provided for @logoutConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定退出登录吗？'**
  String get logoutConfirm;

  /// No description provided for @about.
  ///
  /// In zh, this message translates to:
  /// **'关于'**
  String get about;

  /// No description provided for @aboutBody.
  ///
  /// In zh, this message translates to:
  /// **'知识匣 · 自托管 AI 知识库\n当前版本 0.1.0'**
  String get aboutBody;

  /// No description provided for @errorGeneric.
  ///
  /// In zh, this message translates to:
  /// **'出错了，请重试'**
  String get errorGeneric;

  /// No description provided for @invalidUrl.
  ///
  /// In zh, this message translates to:
  /// **'网址格式不正确'**
  String get invalidUrl;

  /// No description provided for @requiredField.
  ///
  /// In zh, this message translates to:
  /// **'必填'**
  String get requiredField;

  /// No description provided for @done.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get done;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}

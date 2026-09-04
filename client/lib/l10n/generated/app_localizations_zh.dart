// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appTitle => '知识匣';

  @override
  String get serverAddress => '服务器地址';

  @override
  String get serverAddressHint => 'https://your-server.com';

  @override
  String get username => '用户名';

  @override
  String get password => '密码';

  @override
  String get inviteCode => '邀请码（选填）';

  @override
  String get login => '登录';

  @override
  String get register => '注册';

  @override
  String get registerAccount => '注册账号';

  @override
  String get hasAccountGoLogin => '已有账号？去登录';

  @override
  String get noAccountGoRegister => '没有账号？去注册';

  @override
  String get loginFailed => '登录失败';

  @override
  String get networkError => '网络错误，请检查服务器地址';

  @override
  String get homeTitle => '知识流';

  @override
  String get searchHint => '搜索知识卡…';

  @override
  String get statusAll => '全部';

  @override
  String get statusPending => '排队中';

  @override
  String get statusProcessing => '处理中';

  @override
  String get statusReady => '就绪';

  @override
  String get statusFailed => '失败';

  @override
  String get emptyList => '还没有知识卡，点右下角 + 添加';

  @override
  String get emptyListFiltered => '当前筛选没有知识卡';

  @override
  String get loadMoreFailed => '加载更多失败';

  @override
  String get addTitle => '添加知识卡';

  @override
  String get addUrlTab => '网页 URL';

  @override
  String get addPasteTab => '粘贴文本';

  @override
  String get addUrlLabel => '网页地址';

  @override
  String get addUrlHint => 'https://example.com/article';

  @override
  String get addPasteTitleLabel => '标题（选填）';

  @override
  String get addPasteTextLabel => '文本内容';

  @override
  String get addPasteFromClipboard => '从剪贴板粘贴';

  @override
  String get addSubmit => '提交';

  @override
  String get addSubmitted => '已加入处理队列';

  @override
  String get addClipboardFound => '检测到剪贴板中的网址，已预填';

  @override
  String get detailTitle => '知识卡';

  @override
  String get summary => '摘要';

  @override
  String get tags => '标签';

  @override
  String get noSummary => '分析完成后显示摘要';

  @override
  String get processingHint => '正在处理，稍候自动刷新…';

  @override
  String get failedHint => '处理失败';

  @override
  String get retry => '重试';

  @override
  String get reanalyze => '重新分析';

  @override
  String get edit => '编辑';

  @override
  String get editTitle => '编辑标题';

  @override
  String get editSummary => '编辑摘要';

  @override
  String get save => '保存';

  @override
  String get cancel => '取消';

  @override
  String get delete => '删除';

  @override
  String get deleteConfirm => '确定删除这张知识卡吗？批注与标签关联将一并删除。';

  @override
  String get openSource => '打开原文';

  @override
  String wordCount(int count) {
    return '$count 字';
  }

  @override
  String get searchTitle => '搜索';

  @override
  String get searchMode => '检索模式';

  @override
  String get modeHybrid => '混合';

  @override
  String get modeKeyword => '关键词';

  @override
  String get modeSemantic => '语义';

  @override
  String get filterTag => '标签筛选';

  @override
  String get filterStatus => '状态筛选';

  @override
  String get noResults => '没有找到相关知识卡';

  @override
  String get searchFirst => '输入关键词开始检索';

  @override
  String get detailPlaceholder => '选择左侧卡片查看详情';

  @override
  String get matchedKeyword => '关键词';

  @override
  String get matchedSemantic => '语义';

  @override
  String get tagsTitle => '标签管理';

  @override
  String tagCount(int count) {
    return '$count 张卡片';
  }

  @override
  String get renameTag => '重命名';

  @override
  String get mergeTag => '合并到…';

  @override
  String mergeTagInto(String name) {
    return '将「$name」合并到';
  }

  @override
  String get mergeConfirm => '合并';

  @override
  String get deleteTagConfirm => '确定删除该标签吗？卡片本身不受影响。';

  @override
  String get noTags => '还没有标签，采集几张卡片后自动生成';

  @override
  String get settingsTitle => '设置';

  @override
  String get themeMode => '外观';

  @override
  String get themeSystem => '跟随系统';

  @override
  String get themeLight => '浅色';

  @override
  String get themeDark => '深色';

  @override
  String get logout => '退出登录';

  @override
  String get logoutConfirm => '确定退出登录吗？';

  @override
  String get about => '关于';

  @override
  String get aboutBody => '知识匣 · 自托管 AI 知识库\n当前版本 0.1.0';

  @override
  String get errorGeneric => '出错了，请重试';

  @override
  String get invalidUrl => '网址格式不正确';

  @override
  String get requiredField => '必填';

  @override
  String get done => '完成';
}

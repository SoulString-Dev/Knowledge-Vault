/// 服务端 DTO：与架构文档 5.2/5.3 的响应结构一一对应（手写不可变模型）。
library;

class Tokens {
  const Tokens({required this.accessToken, required this.refreshToken, required this.expiresIn});

  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  factory Tokens.fromJson(Map<String, dynamic> json) => Tokens(
    accessToken: json['access_token'] as String,
    refreshToken: json['refresh_token'] as String,
    expiresIn: (json['expires_in'] as num?)?.toInt() ?? 1800,
  );

  Map<String, dynamic> toJson() => {
    'access_token': accessToken,
    'refresh_token': refreshToken,
    'expires_in': expiresIn,
  };
}

class User {
  const User({required this.id, required this.username, required this.isAdmin, this.createdAt});

  final int id;
  final String username;
  final bool isAdmin;
  final DateTime? createdAt;

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'] as int,
    username: json['username'] as String,
    isAdmin: json['is_admin'] as bool? ?? false,
    createdAt: json['created_at'] == null ? null : DateTime.parse(json['created_at'] as String),
  );
}

class Article {
  const Article({
    required this.id,
    required this.url,
    required this.status,
    this.domain,
    this.title,
    this.author,
    this.publishedAt,
    this.wordCount,
    this.summary,
    this.error,
    this.hasSnapshot = false,
    this.createdAt,
    this.updatedAt,
  });

  final int id;
  final String url;
  final String status; // pending | processing | ready | failed
  final String? domain;
  final String? title;
  final String? author;
  final DateTime? publishedAt;
  final int? wordCount;
  final String? summary;
  final String? error;
  final bool hasSnapshot;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get isProcessing => status == 'pending' || status == 'processing';

  factory Article.fromJson(Map<String, dynamic> json) => Article(
    id: json['id'] as int,
    url: json['url'] as String,
    status: json['status'] as String,
    domain: json['domain'] as String?,
    title: json['title'] as String?,
    author: json['author'] as String?,
    publishedAt: json['published_at'] == null
        ? null
        : DateTime.tryParse(json['published_at'] as String),
    wordCount: (json['word_count'] as num?)?.toInt(),
    summary: json['summary'] as String?,
    error: json['error'] as String?,
    hasSnapshot: json['has_snapshot'] as bool? ?? false,
    createdAt: json['created_at'] == null ? null : DateTime.tryParse(json['created_at'] as String),
    updatedAt: json['updated_at'] == null ? null : DateTime.tryParse(json['updated_at'] as String),
  );
}

class Tag {
  const Tag({required this.id, required this.name, this.articleCount = 0});

  final int id;
  final String name;
  final int articleCount;

  factory Tag.fromJson(Map<String, dynamic> json) => Tag(
    id: json['id'] as int,
    name: json['name'] as String,
    articleCount: (json['article_count'] as num?)?.toInt() ?? 0,
  );
}

class ArticleDetail {
  const ArticleDetail({
    required this.article,
    required this.contentMd,
    required this.tags,
    this.contentText,
  });

  final Article article;
  final String? contentMd;
  final String? contentText;
  final List<Tag> tags;

  factory ArticleDetail.fromJson(Map<String, dynamic> json) => ArticleDetail(
    article: Article.fromJson(json),
    contentMd: json['content_md'] as String?,
    contentText: json['content_text'] as String?,
    tags: [
      for (final t in (json['tags'] as List? ?? [])) Tag.fromJson(t as Map<String, dynamic>),
    ],
  );
}

class ArticlePage {
  const ArticlePage({required this.total, required this.page, required this.items});

  final int total;
  final int page;
  final List<Article> items;

  factory ArticlePage.fromJson(Map<String, dynamic> json) => ArticlePage(
    total: json['total'] as int,
    page: json['page'] as int,
    items: [
      for (final a in (json['items'] as List? ?? [])) Article.fromJson(a as Map<String, dynamic>),
    ],
  );
}

class SearchResult {
  const SearchResult({
    required this.articleId,
    required this.url,
    required this.status,
    required this.score,
    required this.matchedBy,
    this.title,
    this.snippet,
    this.tags = const [],
  });

  final int articleId;
  final String? title;
  final String url;
  final String status;
  final double score;
  final String? snippet;
  final List<String> tags;
  final List<String> matchedBy;

  factory SearchResult.fromJson(Map<String, dynamic> json) => SearchResult(
    articleId: json['article_id'] as int,
    title: json['title'] as String?,
    url: json['url'] as String,
    status: json['status'] as String,
    score: (json['score'] as num?)?.toDouble() ?? 0,
    snippet: json['snippet'] as String?,
    tags: [for (final t in (json['tags'] as List? ?? [])) t as String],
    matchedBy: [for (final m in (json['matched_by'] as List? ?? [])) m as String],
  );
}

class SearchResponse {
  const SearchResponse({required this.total, required this.results});

  final int total;
  final List<SearchResult> results;

  factory SearchResponse.fromJson(Map<String, dynamic> json) => SearchResponse(
    total: json['total'] as int,
    results: [
      for (final r in (json['results'] as List? ?? []))
        SearchResult.fromJson(r as Map<String, dynamic>),
    ],
  );
}

class ApiError implements Exception {
  const ApiError(this.code, this.message, {this.status = 0});

  final String code;
  final String message;
  final int status;

  factory ApiError.fromJson(Map<String, dynamic> json, {int status = 0}) => ApiError(
    json['code'] as String? ?? 'UNKNOWN',
    json['message'] as String? ?? '未知错误',
    status: status,
  );

  @override
  String toString() => message;
}

/// 类型化端点封装：路径与架构文档 5.2 端点清单一一对应。
library;

import 'api_client.dart';
import 'models.dart';

class VaultApi {
  VaultApi(this._client);

  final ApiClient _client;

  static const _base = '/api/v1';

  // ---------- auth ----------

  Future<Tokens> login(String username, String password) async {
    final json = await _client.sendJson(
      'POST',
      '$_base/auth/login',
      body: {'username': username, 'password': password},
    );
    return Tokens.fromJson(json);
  }

  Future<Tokens> register(String username, String password, String? inviteCode) async {
    final json = await _client.sendJson(
      'POST',
      '$_base/auth/register',
      body: {'username': username, 'password': password, if (inviteCode != null) 'invite_code': inviteCode},
    );
    return Tokens.fromJson(json);
  }

  Future<User> me() async {
    final json = await _client.getJson('$_base/auth/me');
    return User.fromJson(json);
  }

  Future<void> logout(String refreshToken) =>
      _client.sendVoid('POST', '$_base/auth/logout', body: {'refresh_token': refreshToken});

  // ---------- articles ----------

  Future<ArticlePage> articles({
    int page = 1,
    int pageSize = 20,
    String? q,
    int? tagId,
    String? domain,
    String? status,
    String sort = 'created',
  }) async {
    final json = await _client.getJson(
      '$_base/articles',
      query: {
        'page': page,
        'page_size': pageSize,
        if (q != null && q.isNotEmpty) 'q': q,
        if (tagId != null) 'tag_id': tagId,
        if (domain != null && domain.isNotEmpty) 'domain': domain,
        if (status != null && status.isNotEmpty) 'status': status,
        'sort': sort,
      },
    );
    return ArticlePage.fromJson(json);
  }

  Future<Article> createArticle(String url) async {
    final json = await _client.sendJson('POST', '$_base/articles', body: {'url': url});
    return Article.fromJson(json);
  }

  Future<Article> pasteArticle({String? title, required String text}) async {
    final json = await _client.sendJson(
      'POST',
      '$_base/articles/paste',
      body: {if (title != null && title.isNotEmpty) 'title': title, 'text': text},
    );
    return Article.fromJson(json);
  }

  Future<ArticleDetail> article(int id) async {
    final json = await _client.getJson('$_base/articles/$id');
    return ArticleDetail.fromJson(json);
  }

  Future<Article> patchArticle(
    int id, {
    String? title,
    String? summary,
    String? contentMd,
  }) async {
    final json = await _client.sendJson(
      'PATCH',
      '$_base/articles/$id',
      body: {
        if (title != null) 'title': title,
        if (summary != null) 'summary': summary,
        if (contentMd != null) 'content_md': contentMd,
      },
    );
    return Article.fromJson(json);
  }

  Future<void> deleteArticle(int id) => _client.sendVoid('DELETE', '$_base/articles/$id');

  Future<Article> reanalyze(int id) async {
    final json = await _client.sendJson('POST', '$_base/articles/$id/reanalyze');
    return Article.fromJson(json);
  }

  Future<Article> retryArticle(int id, {String? text}) async {
    final json = await _client.sendJson(
      'POST',
      '$_base/articles/$id/retry',
      body: {if (text != null) 'text': text},
    );
    return Article.fromJson(json);
  }

  // ---------- search ----------

  Future<SearchResponse> search({
    required String query,
    String mode = 'hybrid',
    int? tagId,
    String? status,
  }) async {
    final json = await _client.sendJson(
      'POST',
      '$_base/search',
      body: {
        'query': query,
        'mode': mode,
        'filters': {if (tagId != null) 'tag_id': tagId, if (status != null && status.isNotEmpty) 'status': status},
      },
    );
    return SearchResponse.fromJson(json);
  }

  // ---------- tags ----------

  Future<List<Tag>> tags() async {
    final list = await _client.getList('$_base/tags');
    return [for (final t in list) Tag.fromJson(t as Map<String, dynamic>)];
  }

  Future<Tag> renameTag(int id, String name) async {
    final json = await _client.sendJson('PATCH', '$_base/tags/$id', body: {'name': name});
    return Tag.fromJson(json);
  }

  Future<void> deleteTag(int id) => _client.sendVoid('DELETE', '$_base/tags/$id');

  Future<void> mergeTag(int srcId, int dstId) =>
      _client.sendVoid('POST', '$_base/tags/merge', body: {'src_id': srcId, 'dst_id': dstId});
}

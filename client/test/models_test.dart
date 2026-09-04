/// 模型 JSON 解析测试（与服务端 5.3 响应结构对齐）。
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/core/models.dart';

void main() {
  test('ArticlePage.fromJson 解析列表响应', () {
    final page = ArticlePage.fromJson({
      'total': 3,
      'page': 1,
      'page_size': 20,
      'items': [
        {
          'id': 42,
          'url': 'https://example.com/post/123',
          'status': 'ready',
          'domain': 'example.com',
          'title': 'Redis 分布式锁实战',
          'summary': '这是一段摘要',
          'word_count': 1200,
          'has_snapshot': true,
          'created_at': '2026-09-05T00:00:00+00:00',
        },
        {'id': 43, 'url': 'paste://1/abc', 'status': 'pending'},
      ],
    });
    expect(page.total, 3);
    expect(page.items.length, 2);
    expect(page.items[0].title, 'Redis 分布式锁实战');
    expect(page.items[0].hasSnapshot, isTrue);
    expect(page.items[0].isProcessing, isFalse);
    expect(page.items[1].isProcessing, isTrue);
  });

  test('ArticleDetail.fromJson 解析详情响应', () {
    final detail = ArticleDetail.fromJson({
      'id': 42,
      'url': 'https://example.com/a',
      'status': 'ready',
      'summary': '摘要',
      'content_md': '# 标题\n正文',
      'tags': [
        {'id': 1, 'name': 'redis'},
        {'id': 2, 'name': '分布式'},
      ],
    });
    expect(detail.contentMd, contains('正文'));
    expect(detail.tags.map((t) => t.name), ['redis', '分布式']);
  });

  test('SearchResponse.fromJson 解析混合检索响应', () {
    final resp = SearchResponse.fromJson({
      'total': 1,
      'results': [
        {
          'article_id': 42,
          'title': 'Redis 分布式锁实战',
          'url': 'https://example.com/post/123',
          'status': 'ready',
          'score': 0.0332,
          'snippet': '…可重入锁的<em>坑</em>主要有三点…',
          'tags': ['redis', '分布式'],
          'matched_by': ['keyword', 'semantic'],
        },
      ],
    });
    expect(resp.results.single.matchedBy, containsAll(['keyword', 'semantic']));
    expect(resp.results.single.snippet, contains('<em>'));
  });

  test('Tokens 往返序列化', () {
    const tokens = Tokens(accessToken: 'a', refreshToken: 'r', expiresIn: 1800);
    final restored = Tokens.fromJson(tokens.toJson());
    expect(restored.accessToken, 'a');
    expect(restored.refreshToken, 'r');
  });
}

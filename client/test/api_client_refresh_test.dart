/// 401 单飞刷新（6.1）核心行为测试：
/// 1) 401 → 刷新 → 重放成功；2) 并发 401 只触发一次 refresh；3) 刷新失败清空凭据。
library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/core/api_client.dart';
import 'package:knowledge_vault/core/models.dart';
import 'package:knowledge_vault/core/storage.dart';

class FakeStorage extends AppStorage {
  final Map<String, String> _mem = {};

  @override
  Future<String?> readBaseUrl() async => 'https://test.local';

  @override
  Future<String?> readAccessToken() async => _mem['access'];

  @override
  Future<String?> readRefreshToken() async => _mem['refresh'];

  @override
  Future<void> writeTokens({required String access, required String refresh}) async {
    _mem['access'] = access;
    _mem['refresh'] = refresh;
  }

  @override
  Future<void> clearTokens() async => _mem.clear();
}

class MockAdapter implements HttpClientAdapter {
  MockAdapter(this.handler);

  final Future<ResponseBody> Function(RequestOptions options) handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) => handler(options);

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonBody(Object json, {int status = 200}) =>
    ResponseBody.fromString(jsonEncode(json), status, headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});

void main() {
  test('401 后刷新并重放成功', () async {
    var refreshCalls = 0;
    final client = ApiClient(
      storage: FakeStorage(),
      onAuthLost: () {},
      adapter: MockAdapter((options) async {
        if (options.path.contains('/auth/refresh')) {
          refreshCalls++;
          return jsonBody({'access_token': 'new-access', 'refresh_token': 'new-refresh'});
        }
        final auth = options.headers['Authorization'] as String? ?? '';
        if (auth == 'Bearer new-access') {
          return jsonBody({'total': 0, 'page': 1, 'items': []});
        }
        return ResponseBody.fromString('{"code": "TOKEN_EXPIRED"}', 401, headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        });
      }),
    );
    await client.configure(baseUrl: 'https://test.local');
    await client.setTokens(const Tokens(accessToken: 'old', refreshToken: 'r', expiresIn: 1));

    final resp = await client.getJson('/api/v1/articles');
    expect(resp['total'], 0);
    expect(refreshCalls, 1);
    client.dispose();
  });

  test('并发 401 只触发一次 refresh（单飞）', () async {
    var refreshCalls = 0;
    final client = ApiClient(
      storage: FakeStorage(),
      onAuthLost: () {},
      adapter: MockAdapter((options) async {
        if (options.path.contains('/auth/refresh')) {
          refreshCalls++;
          await Future<void>.delayed(const Duration(milliseconds: 50));
          return jsonBody({'access_token': 'new-access', 'refresh_token': 'new-refresh'});
        }
        final auth = options.headers['Authorization'] as String? ?? '';
        return auth == 'Bearer new-access'
            ? jsonBody({'total': 0, 'page': 1, 'items': []})
            : ResponseBody.fromString('{"code": "TOKEN_EXPIRED"}', 401, headers: {
                Headers.contentTypeHeader: [Headers.jsonContentType],
              });
      }),
    );
    await client.configure(baseUrl: 'https://test.local');
    await client.setTokens(const Tokens(accessToken: 'old', refreshToken: 'r', expiresIn: 1));

    final results = await Future.wait([
      client.getJson('/api/v1/articles'),
      client.getJson('/api/v1/articles'),
      client.getJson('/api/v1/tags'),
    ]);
    expect(results.length, 3);
    expect(refreshCalls, 1, reason: '并发 401 必须共享同一次 refresh');
    client.dispose();
  });

  test('refresh 失败 → 清空凭据并回调 onAuthLost', () async {
    var authLost = 0;
    final storage = FakeStorage();
    final client = ApiClient(
      storage: storage,
      onAuthLost: () => authLost++,
      adapter: MockAdapter((options) async {
        if (options.path.contains('/auth/refresh')) {
          return ResponseBody.fromString('{"code": "REFRESH_REUSED"}', 401, headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          });
        }
        return ResponseBody.fromString('{"code": "TOKEN_EXPIRED"}', 401, headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        });
      }),
    );
    await client.configure(baseUrl: 'https://test.local');
    await client.setTokens(const Tokens(accessToken: 'old', refreshToken: 'r', expiresIn: 1));

    await expectLater(client.getJson('/api/v1/articles'), throwsA(isA<ApiError>()));
    expect(authLost, 1);
    expect(await storage.readRefreshToken(), isNull);
    client.dispose();
  });
}

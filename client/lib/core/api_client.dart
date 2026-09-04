/// dio 网络客户端：统一鉴权头、401 单飞（single-flight）刷新后重放（6.1），
/// 服务端统一错误体 → [ApiError]。
library;

import 'package:dio/dio.dart';

import 'models.dart';
import 'storage.dart';

class ApiClient {
  ApiClient({
    required AppStorage storage,
    required void Function() onAuthLost,
    HttpClientAdapter? adapter,
  }) : _storage = storage,
       _onAuthLost = onAuthLost {
    _dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
        // 保持默认：非 2xx 抛 DioException → onError 拦截器才能处理 401 刷新
      ),
    );
    if (adapter != null) {
      _dio.httpClientAdapter = adapter; // 测试注入口
    }
    _dio.interceptors.add(
      InterceptorsWrapper(onRequest: _attachToken, onError: _handleError),
    );
  }

  final AppStorage _storage;
  final void Function() _onAuthLost;
  late final Dio _dio;
  String? _accessToken;
  Future<bool>? _refreshFuture;

  static const _skipAuthPaths = ['/auth/login', '/auth/register', '/auth/refresh'];

  /// 应用启动 / 登录时配置服务器地址与已存 token。
  Future<void> configure({required String baseUrl}) async {
    _dio.options.baseUrl = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    _accessToken = await _storage.readAccessToken();
  }

  String get baseUrl => _dio.options.baseUrl;
  bool get hasBaseUrl => _dio.options.baseUrl.isNotEmpty;

  void dispose() => _dio.close();

  Future<void> setTokens(Tokens tokens) async {
    _accessToken = tokens.accessToken;
    await _storage.writeTokens(access: tokens.accessToken, refresh: tokens.refreshToken);
  }

  Future<void> clearTokens() async {
    _accessToken = null;
    await _storage.clearTokens();
  }

  void _attachToken(RequestOptions options, RequestInterceptorHandler handler) async {
    final path = options.path;
    final skip = _skipAuthPaths.any((p) => path.contains(p));
    if (!skip) {
      _accessToken ??= await _storage.readAccessToken();
      final token = _accessToken;
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }
    handler.next(options);
  }

  Future<void> _handleError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final response = err.response;
    final status = response?.statusCode;
    final req = err.requestOptions;
    final alreadyRetried = req.extra['retried'] == true;
    final isAuthPath = _skipAuthPaths.any((p) => req.path.contains(p));

    if (status == 401 && !alreadyRetried && !isAuthPath) {
      final ok = await _refreshSingleFlight();
      if (ok) {
        try {
          req.extra['retried'] = true;
          req.headers['Authorization'] = 'Bearer ${_accessToken ?? ''}';
          final resp = await _dio.fetch<dynamic>(req);
          return handler.resolve(resp);
        } on DioException catch (retryErr) {
          return handler.next(retryErr);
        }
      }
      _onAuthLost();
    }
    handler.next(err);
  }

  /// 单飞：并发 401 只发起一次 refresh，其余请求共享同一结果（防止并发轮换触发盗用检测）。
  Future<bool> _refreshSingleFlight() {
    return _refreshFuture ??= _doRefresh().whenComplete(() => _refreshFuture = null);
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return false;
    }
    try {
      final resp = await _dio.post<Map<String, dynamic>>(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(extra: {'skipAuth': true}),
      );
      final tokens = Tokens.fromJson(resp.data!);
      _accessToken = tokens.accessToken;
      await _storage.writeTokens(access: tokens.accessToken, refresh: tokens.refreshToken);
      return true;
    } on DioException {
      _accessToken = null;
      await _storage.clearTokens();
      return false;
    }
  }

  ApiError _toApiError(DioException err) {
    final status = err.response?.statusCode ?? 0;
    final data = err.response?.data;
    if (data is Map<String, dynamic>) {
      return ApiError.fromJson(data, status: status);
    }
    if (status == 0) {
      return const ApiError('NETWORK', '网络错误，请检查服务器地址', status: 0);
    }
    return ApiError('HTTP_$status', '请求失败（HTTP $status）', status: status);
  }

  /// GET 并解析 JSON；非 2xx 抛 [ApiError]。
  Future<Map<String, dynamic>> getJson(String path, {Map<String, dynamic>? query}) async {
    try {
      final resp = await _dio.get<Map<String, dynamic>>(path, queryParameters: query);
      if ((resp.statusCode ?? 500) >= 400) {
        throw _toApiError(DioException(requestOptions: RequestOptions(path: path), response: resp));
      }
      return resp.data ?? <String, dynamic>{};
    } on DioException catch (e) {
      throw _toApiError(e);
    }
  }

  Future<List<dynamic>> getList(String path, {Map<String, dynamic>? query}) async {
    try {
      final resp = await _dio.get<List<dynamic>>(path, queryParameters: query);
      if ((resp.statusCode ?? 500) >= 400) {
        throw _toApiError(DioException(requestOptions: RequestOptions(path: path), response: resp));
      }
      return resp.data ?? <dynamic>[];
    } on DioException catch (e) {
      throw _toApiError(e);
    }
  }

  Future<Map<String, dynamic>> sendJson(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    try {
      final resp = await _dio.request<dynamic>(
        path,
        data: body,
        options: Options(method: method),
      );
      if ((resp.statusCode ?? 500) >= 400) {
        throw _toApiError(DioException(requestOptions: RequestOptions(path: path), response: resp));
      }
      return resp.data is Map<String, dynamic> ? resp.data as Map<String, dynamic> : {};
    } on DioException catch (e) {
      throw _toApiError(e);
    }
  }

  Future<void> sendVoid(String method, String path, {Map<String, dynamic>? body}) async {
    try {
      final resp = await _dio.request<dynamic>(
        path,
        data: body,
        options: Options(method: method),
      );
      if ((resp.statusCode ?? 500) >= 400) {
        throw _toApiError(DioException(requestOptions: RequestOptions(path: path), response: resp));
      }
    } on DioException catch (e) {
      throw _toApiError(e);
    }
  }
}

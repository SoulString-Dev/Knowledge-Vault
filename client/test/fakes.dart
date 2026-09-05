/// 测试公共桩：内存版存储与可配置失败的 API。
library;

import 'package:knowledge_vault/core/api.dart';
import 'package:knowledge_vault/core/api_client.dart';
import 'package:knowledge_vault/core/models.dart';
import 'package:knowledge_vault/core/storage.dart';

/// 内存版 AppStorage：不触碰平台通道，可在 flutter test 中直接使用。
class FakeStorage extends AppStorage {
  final Map<String, String> _strings = <String, String>{};
  int? _themeMode;

  String? get storedBaseUrl => _strings['base_url'];
  String? get storedRefreshToken => _strings['refresh'];

  @override
  Future<String?> readBaseUrl() async => _strings['base_url'];

  @override
  Future<void> writeBaseUrl(String url) async => _strings['base_url'] = url;

  @override
  Future<String?> readAccessToken() async => _strings['access'];

  @override
  Future<String?> readRefreshToken() async => _strings['refresh'];

  @override
  Future<void> writeTokens({required String access, required String refresh}) async {
    _strings['access'] = access;
    _strings['refresh'] = refresh;
  }

  @override
  Future<void> clearTokens() async {
    _strings.remove('access');
    _strings.remove('refresh');
  }

  @override
  Future<int> readThemeMode() async => _themeMode ?? 0;

  @override
  Future<void> writeThemeMode(int mode) async => _themeMode = mode;
}

/// 内存版 VaultApi：按标志位决定登录 / 注册是否失败，用于会话流程测试。
class FakeVaultApi extends VaultApi {
  FakeVaultApi() : super(_unusedClient());

  static ApiClient _unusedClient() => ApiClient(storage: FakeStorage(), onAuthLost: () {});

  bool failLogin = false;
  bool failRegister = false;
  String? logoutCalledWith;

  final User currentUser = const User(id: 1, username: 'alice', isAdmin: true);

  @override
  Future<Tokens> login(String username, String password) async {
    if (failLogin) {
      throw const ApiError('INVALID_CREDENTIALS', '用户名或密码错误', status: 401);
    }
    return const Tokens(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 1800);
  }

  @override
  Future<Tokens> register(String username, String password, String? inviteCode) async {
    if (failRegister) {
      throw const ApiError('USERNAME_TAKEN', '用户名已存在', status: 409);
    }
    return const Tokens(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 1800);
  }

  @override
  Future<User> me() async => currentUser;

  @override
  Future<void> logout(String refreshToken) async => logoutCalledWith = refreshToken;
}

/// 本地持久化：凭据入安全存储（Android Keystore / Windows DPAPI，FR4.3），
/// 服务器地址与外观偏好入 SharedPreferences。
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppStorage {
  AppStorage({FlutterSecureStorage? secure, SharedPreferences? prefs})
    : _secure = secure ?? const FlutterSecureStorage(
        aOptions: AndroidOptions(encryptedSharedPreferences: true),
      ),
      _prefs = prefs;

  final FlutterSecureStorage _secure;
  final SharedPreferences? _prefs;

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _kBaseUrl = 'base_url';
  static const _kThemeMode = 'theme_mode';

  Future<String?> readBaseUrl() async => _prefs?.getString(_kBaseUrl);
  Future<void> writeBaseUrl(String url) async => _prefs?.setString(_kBaseUrl, url);

  Future<String?> readAccessToken() => _secure.read(key: _kAccess);
  Future<String?> readRefreshToken() => _secure.read(key: _kRefresh);

  Future<void> writeTokens({required String access, required String refresh}) async {
    await _secure.write(key: _kAccess, value: access);
    await _secure.write(key: _kRefresh, value: refresh);
  }

  Future<void> clearTokens() async {
    await _secure.delete(key: _kAccess);
    await _secure.delete(key: _kRefresh);
  }

  /// themeMode: 0 = system, 1 = light, 2 = dark
  Future<int> readThemeMode() async => _prefs?.getInt(_kThemeMode) ?? 0;
  Future<void> writeThemeMode(int mode) async => _prefs?.setInt(_kThemeMode, mode);
}

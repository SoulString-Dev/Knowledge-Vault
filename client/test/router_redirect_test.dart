/// 路由重定向决策测试（对应登录后状态不切换的回归修复）。
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/core/router.dart';
import 'package:knowledge_vault/core/session.dart';

void main() {
  test('loading：一律回启动页', () {
    expect(sessionRedirect(SessionStatus.loading, '/'), isNull);
    expect(sessionRedirect(SessionStatus.loading, '/login'), '/');
    expect(sessionRedirect(SessionStatus.loading, '/home'), '/');
  });

  test('loggedOut：允许登录/注册页，其余踢到登录页', () {
    expect(sessionRedirect(SessionStatus.loggedOut, '/login'), isNull);
    expect(sessionRedirect(SessionStatus.loggedOut, '/register'), isNull);
    expect(sessionRedirect(SessionStatus.loggedOut, '/home'), '/login');
    expect(sessionRedirect(SessionStatus.loggedOut, '/settings'), '/login');
  });

  test('loggedIn：登录/注册页与启动页进 /home，业务页放行', () {
    expect(sessionRedirect(SessionStatus.loggedIn, '/login'), '/home');
    expect(sessionRedirect(SessionStatus.loggedIn, '/register'), '/home');
    expect(sessionRedirect(SessionStatus.loggedIn, '/'), '/home');
    expect(sessionRedirect(SessionStatus.loggedIn, '/home'), isNull);
    expect(sessionRedirect(SessionStatus.loggedIn, '/article/42'), isNull);
    expect(sessionRedirect(SessionStatus.loggedIn, '/search'), isNull);
  });
}

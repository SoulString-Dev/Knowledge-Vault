/// 路由：go_router + 会话状态重定向。
///
/// 注意：GoRouter 实例必须只创建一次（不能 watch 会话状态），
/// 通过 refreshListenable 在会话变化时重新执行 redirect（redirect 内用 ref.read）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/add/add_page.dart';
import '../features/article/article_detail_page.dart';
import '../features/auth/login_page.dart';
import '../features/auth/register_page.dart';
import '../features/home/home_page.dart';
import '../features/search/search_page.dart';
import '../features/settings/settings_page.dart';
import '../features/tags/tags_page.dart';
import '../features/splash/splash_page.dart';
import 'session.dart';

/// 会话状态 → 路由决策（纯函数，便于单测）。
String? sessionRedirect(SessionStatus status, String matchedLocation) {
  final loggingIn = matchedLocation == '/login' || matchedLocation == '/register';
  switch (status) {
    case SessionStatus.loading:
      return matchedLocation == '/' ? null : '/';
    case SessionStatus.loggedOut:
      return loggingIn ? null : '/login';
    case SessionStatus.loggedIn:
      if (loggingIn || matchedLocation == '/') return '/home';
      return null;
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  // 会话状态变化 → 触发 redirect 重新执行；router 本身不重建
  final refresh = ValueNotifier<int>(0);
  ref.listen(sessionControllerProvider, (previous, next) => refresh.value++);
  ref.onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final session = ref.read(sessionControllerProvider);
      final status = session.valueOrNull?.status ?? SessionStatus.loading;
      return sessionRedirect(status, state.matchedLocation);
    },
    routes: [
      GoRoute(path: '/', builder: (c, s) => const SplashPage()),
      GoRoute(path: '/login', builder: (c, s) => const LoginPage()),
      GoRoute(path: '/register', builder: (c, s) => const RegisterPage()),
      GoRoute(path: '/home', builder: (c, s) => const HomePage()),
      GoRoute(
        path: '/article/:id',
        builder: (c, s) => ArticleDetailPage(articleId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(path: '/add', builder: (c, s) => const AddPage()),
      GoRoute(path: '/search', builder: (c, s) => const SearchPage()),
      GoRoute(path: '/tags', builder: (c, s) => const TagsPage()),
      GoRoute(path: '/settings', builder: (c, s) => const SettingsPage()),
    ],
  );
});

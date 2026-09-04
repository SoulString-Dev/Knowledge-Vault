/// 路由：go_router + 会话状态重定向。
library;

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

final routerProvider = Provider<GoRouter>((ref) {
  final session = ref.watch(sessionControllerProvider);
  final status = session.value?.status ?? SessionStatus.loading;

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final loggingIn =
          state.matchedLocation == '/login' || state.matchedLocation == '/register';
      switch (status) {
        case SessionStatus.loading:
          return state.matchedLocation == '/' ? null : '/';
        case SessionStatus.loggedOut:
          return loggingIn ? null : '/login';
        case SessionStatus.loggedIn:
          if (loggingIn || state.matchedLocation == '/') return '/home';
          return null;
      }
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

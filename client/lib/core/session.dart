/// 会话状态与全局 Provider 装配。
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api.dart';
import 'api_client.dart';
import 'models.dart';
import 'storage.dart';

export 'api.dart';
export 'models.dart';

enum SessionStatus { loading, loggedOut, loggedIn }

class SessionState {
  const SessionState({required this.status, this.user});

  final SessionStatus status;
  final User? user;
}

final storageProvider = Provider<AppStorage>((ref) => AppStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient(
    storage: ref.watch(storageProvider),
    onAuthLost: () => ref.read(sessionControllerProvider.notifier).onAuthLost(),
  );
  ref.onDispose(client.dispose);
  return client;
});

final vaultApiProvider = Provider<VaultApi>((ref) => VaultApi(ref.watch(apiClientProvider)));

class SessionController extends AsyncNotifier<SessionState> {
  @override
  Future<SessionState> build() async {
    final storage = ref.watch(storageProvider);
    final api = ref.watch(vaultApiProvider);
    final client = ref.watch(apiClientProvider);

    final baseUrl = await storage.readBaseUrl();
    if (baseUrl == null || baseUrl.isEmpty) {
      return const SessionState(status: SessionStatus.loggedOut);
    }
    await client.configure(baseUrl: baseUrl);
    final refresh = await storage.readRefreshToken();
    if (refresh == null || refresh.isEmpty) {
      return const SessionState(status: SessionStatus.loggedOut);
    }
    try {
      final user = await api.me();
      return SessionState(status: SessionStatus.loggedIn, user: user);
    } on ApiError {
      await client.clearTokens();
      return const SessionState(status: SessionStatus.loggedOut);
    }
  }

  Future<void> login(String baseUrl, String username, String password) async {
    final storage = ref.watch(storageProvider);
    final api = ref.watch(vaultApiProvider);
    final client = ref.watch(apiClientProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await client.configure(baseUrl: baseUrl);
      final tokens = await api.login(username, password);
      await client.setTokens(tokens);
      await storage.writeBaseUrl(baseUrl);
      final user = await api.me();
      return SessionState(status: SessionStatus.loggedIn, user: user);
    });
  }

  Future<void> register(String baseUrl, String username, String password, String? inviteCode) async {
    final storage = ref.watch(storageProvider);
    final api = ref.watch(vaultApiProvider);
    final client = ref.watch(apiClientProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await client.configure(baseUrl: baseUrl);
      final tokens = await api.register(username, password, inviteCode);
      await client.setTokens(tokens);
      await storage.writeBaseUrl(baseUrl);
      final user = await api.me();
      return SessionState(status: SessionStatus.loggedIn, user: user);
    });
  }

  Future<void> logout() async {
    final api = ref.watch(vaultApiProvider);
    final client = ref.watch(apiClientProvider);
    final storage = ref.watch(storageProvider);
    final refresh = await storage.readRefreshToken();
    if (refresh != null) {
      try {
        await api.logout(refresh);
      } on ApiError {
        // 吊销失败也不阻塞登出
      }
    }
    await client.clearTokens();
    state = const AsyncData(SessionState(status: SessionStatus.loggedOut));
  }

  /// 拦截器发现 refresh 已失效（盗用检测 / 过期）：重置会话。
  void onAuthLost() {
    if (state.value?.status == SessionStatus.loggedIn) {
      state = const AsyncData(SessionState(status: SessionStatus.loggedOut));
    }
  }
}

final sessionControllerProvider =
    AsyncNotifierProvider<SessionController, SessionState>(SessionController.new);

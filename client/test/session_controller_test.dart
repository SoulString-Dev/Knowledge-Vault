/// 会话控制器流程测试：登录成功/失败（失败必须保持登出态且清凭据）、
/// 注册、登出、盗用登出（onAuthLost）。对应「登录后状态不切换」的回归区域。
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/core/session.dart';

import 'fakes.dart';

ProviderContainer _container(FakeVaultApi api, FakeStorage storage) {
  final container = ProviderContainer(
    overrides: [
      storageProvider.overrideWithValue(storage),
      vaultApiProvider.overrideWithValue(api),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

Future<SessionState> _settled(ProviderContainer container) async {
  // 触发 build()（无 baseUrl → loggedOut），等待初始状态就绪
  await container.read(sessionControllerProvider.future);
  return container.read(sessionControllerProvider).requireValue;
}

void main() {
  test('初始无服务器地址：loggedOut', () async {
    final container = _container(FakeVaultApi(), FakeStorage());
    final state = await _settled(container);
    expect(state.status, SessionStatus.loggedOut);
  });

  test('登录成功：loggedIn + 用户信息 + 地址与凭据持久化', () async {
    final api = FakeVaultApi();
    final storage = FakeStorage();
    final container = _container(api, storage);
    await _settled(container);

    await container
        .read(sessionControllerProvider.notifier)
        .login('https://test.local', 'alice', 'password123');

    final state = container.read(sessionControllerProvider).requireValue;
    expect(state.status, SessionStatus.loggedIn);
    expect(state.user?.username, 'alice');
    expect(storage.storedBaseUrl, 'https://test.local');
    expect(storage.storedRefreshToken, 'refresh-1');
  });

  test('登录失败：保持 loggedOut、凭据清空、异常上抛给页面展示', () async {
    final api = FakeVaultApi()..failLogin = true;
    final storage = FakeStorage();
    final container = _container(api, storage);
    await _settled(container);

    await expectLater(
      container
          .read(sessionControllerProvider.notifier)
          .login('https://test.local', 'alice', 'wrong-password'),
      throwsA(isA<ApiError>()),
    );

    final state = container.read(sessionControllerProvider).requireValue;
    expect(state.status, SessionStatus.loggedOut);
    expect(storage.storedRefreshToken, isNull);
    expect(storage.storedBaseUrl, isNull);
  });

  test('注册成功：loggedIn', () async {
    final api = FakeVaultApi();
    final container = _container(api, FakeStorage());
    await _settled(container);

    await container
        .read(sessionControllerProvider.notifier)
        .register('https://test.local', 'bob', 'password123', null);

    expect(
      container.read(sessionControllerProvider).requireValue.status,
      SessionStatus.loggedIn,
    );
  });

  test('注册失败：保持 loggedOut 并上抛', () async {
    final api = FakeVaultApi()..failRegister = true;
    final container = _container(api, FakeStorage());
    await _settled(container);

    await expectLater(
      container
          .read(sessionControllerProvider.notifier)
          .register('https://test.local', 'bob', 'password123', null),
      throwsA(isA<ApiError>()),
    );
    expect(
      container.read(sessionControllerProvider).requireValue.status,
      SessionStatus.loggedOut,
    );
  });

  test('登出：调用服务端吊销并回到 loggedOut', () async {
    final api = FakeVaultApi();
    final container = _container(api, FakeStorage());
    await _settled(container);
    final notifier = container.read(sessionControllerProvider.notifier);
    await notifier.login('https://test.local', 'alice', 'password123');

    await notifier.logout();

    expect(
      container.read(sessionControllerProvider).requireValue.status,
      SessionStatus.loggedOut,
    );
    expect(api.logoutCalledWith, 'refresh-1');
  });

  test('onAuthLost：loggedIn → loggedOut；已登出则状态不变', () async {
    final api = FakeVaultApi();
    final container = _container(api, FakeStorage());
    await _settled(container);
    final notifier = container.read(sessionControllerProvider.notifier);
    await notifier.login('https://test.local', 'alice', 'password123');

    notifier.onAuthLost();
    expect(
      container.read(sessionControllerProvider).requireValue.status,
      SessionStatus.loggedOut,
    );

    // 已经是 loggedOut，再次触发不应抛错或改变状态
    notifier.onAuthLost();
    expect(
      container.read(sessionControllerProvider).requireValue.status,
      SessionStatus.loggedOut,
    );
  });
}

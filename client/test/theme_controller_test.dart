/// 外观偏好持久化测试。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/core/session.dart';
import 'package:knowledge_vault/core/theme.dart';

import 'fakes.dart';

void main() {
  test('setMode 立即生效并持久化；load 读回', () async {
    final storage = FakeStorage();
    final container = ProviderContainer(
      overrides: [storageProvider.overrideWithValue(storage)],
    );
    addTearDown(container.dispose);

    final notifier = container.read(themeControllerProvider.notifier);
    await notifier.load();
    expect(container.read(themeControllerProvider), 0); // 默认跟随系统

    await notifier.setMode(2);
    expect(container.read(themeControllerProvider), 2);
    expect(await storage.readThemeMode(), 2);

    // 模拟重启后 load 读回
    final container2 = ProviderContainer(
      overrides: [storageProvider.overrideWithValue(storage)],
    );
    addTearDown(container2.dispose);
    final notifier2 = container2.read(themeControllerProvider.notifier);
    await notifier2.load();
    expect(container2.read(themeControllerProvider), 2);

    expect(themeModeFromInt(2), ThemeMode.dark);
  });
}

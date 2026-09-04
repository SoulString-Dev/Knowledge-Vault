/// 外观：Material 3，深浅色跟随设置（FR4.6）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'session.dart';

class ThemeController extends Notifier<int> {
  @override
  int build() => 0; // 0 system, 1 light, 2 dark；启动时由 load() 填充

  Future<void> load() async {
    state = await ref.watch(storageProvider).readThemeMode();
  }

  Future<void> setMode(int mode) async {
    state = mode;
    await ref.watch(storageProvider).writeThemeMode(mode);
  }
}

final themeControllerProvider = NotifierProvider<ThemeController, int>(ThemeController.new);

ThemeMode themeModeFromInt(int mode) => switch (mode) {
  1 => ThemeMode.light,
  2 => ThemeMode.dark,
  _ => ThemeMode.system,
};

ThemeData buildTheme(Brightness brightness) {
  final scheme = ColorScheme.fromSeed(seedColor: const Color(0xFF7B5CD6), brightness: brightness);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(horizontal: 12, vertical: 5)),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
      isDense: true,
    ),
  );
}

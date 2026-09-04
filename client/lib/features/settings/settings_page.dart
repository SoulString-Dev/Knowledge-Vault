/// 设置页：外观（深浅色）、退出登录、关于。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../l10n/generated/app_localizations.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final themeMode = ref.watch(themeControllerProvider);
    final session = ref.watch(sessionControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.brightness_6_outlined),
            title: Text(l10n.themeMode),
            trailing: SegmentedButton<int>(
              segments: [
                ButtonSegment(value: 0, label: Text(l10n.themeSystem)),
                ButtonSegment(value: 1, label: Text(l10n.themeLight)),
                ButtonSegment(value: 2, label: Text(l10n.themeDark)),
              ],
              selected: {themeMode},
              onSelectionChanged: (s) =>
                  ref.read(themeControllerProvider.notifier).setMode(s.first),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.logout),
            title: Text(l10n.logout),
            onTap: () async {
              final confirmed = await showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  content: Text(l10n.logoutConfirm),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.cancel)),
                    FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.logout)),
                  ],
                ),
              );
              if (confirmed == true) {
                await ref.read(sessionControllerProvider.notifier).logout();
                if (context.mounted) context.go('/login');
              }
            },
          ),
          AboutListTile(
            icon: const Icon(Icons.info_outline),
            applicationName: l10n.appTitle,
            applicationVersion: session.value?.user?.username == null
                ? l10n.aboutBody
                : '${l10n.aboutBody}\n${session.value!.user!.username}',
          ),
        ],
      ),
    );
  }
}

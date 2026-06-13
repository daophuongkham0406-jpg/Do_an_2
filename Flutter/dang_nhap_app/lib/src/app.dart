import 'package:flutter/material.dart';

import 'core/api_service.dart';
import 'core/app_colors.dart';
import 'features/auth/auth_screen.dart';
import 'features/shell/main_shell.dart';

class FitMeApp extends StatefulWidget {
  const FitMeApp({super.key});

  @override
  State<FitMeApp> createState() => _FitMeAppState();
}

class _FitMeAppState extends State<FitMeApp> {
  AppUser? _user;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'FIT ME',
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.bgMain,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.accentPurple,
          brightness: Brightness.dark,
        ),
        fontFamily: 'Roboto',
      ),
      home: _user == null
          ? AuthScreen(onLoggedIn: (user) => setState(() => _user = user))
          : MainShell(
              user: _user!,
              onLogout: () => setState(() => _user = null),
            ),
    );
  }
}

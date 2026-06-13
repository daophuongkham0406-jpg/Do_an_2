import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

enum AuthMode { login, register }

class AuthScreen extends StatefulWidget {
  const AuthScreen({required this.onLoggedIn, super.key});

  final ValueChanged<AppUser> onLoggedIn;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _api = const ApiService();
  final _loginEmail = TextEditingController();
  final _loginPassword = TextEditingController();
  final _name = TextEditingController();
  final _age = TextEditingController();
  final _username = TextEditingController();
  final _registerEmail = TextEditingController();
  final _registerPassword = TextEditingController();
  final _confirmPassword = TextEditingController();

  AuthMode _mode = AuthMode.login;
  String _gender = 'khac';
  bool _loading = false;
  bool _showLoginPassword = false;
  bool _showRegisterPassword = false;
  bool _showConfirmPassword = false;

  @override
  void dispose() {
    _loginEmail.dispose();
    _loginPassword.dispose();
    _name.dispose();
    _age.dispose();
    _username.dispose();
    _registerEmail.dispose();
    _registerPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final email = _loginEmail.text.trim();
    final password = _loginPassword.text;
    if (email.isEmpty || password.isEmpty) {
      showAppSnack(context, 'Vui lòng nhập email và mật khẩu.', error: true);
      return;
    }

    setState(() => _loading = true);
    final result = await _api.post('/api/auth/login', {
      'email': email,
      'password': password,
    });
    if (!mounted) return;
    setState(() => _loading = false);

    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Đăng nhập thất bại.',
          error: true);
      return;
    }

    final body = _api.mapFrom(result.body);
    final user = body['user'];
    if (user is Map) {
      widget.onLoggedIn(AppUser.fromJson(Map<String, dynamic>.from(user)));
    } else {
      showAppSnack(context, 'Backend không trả về thông tin user.',
          error: true);
    }
  }

  Future<void> _register() async {
    final password = _registerPassword.text;
    final confirm = _confirmPassword.text;
    final regex = RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$');

    if (_name.text.trim().isEmpty ||
        _age.text.trim().isEmpty ||
        _username.text.trim().isEmpty ||
        _registerEmail.text.trim().isEmpty) {
      showAppSnack(context, 'Vui lòng nhập đầy đủ thông tin đăng ký.',
          error: true);
      return;
    }
    if (!regex.hasMatch(password)) {
      showAppSnack(
        context,
        'Mật khẩu phải từ 8 ký tự, có chữ hoa, chữ thường và số.',
        error: true,
      );
      return;
    }
    if (password != confirm) {
      showAppSnack(context, 'Mật khẩu xác nhận không khớp.', error: true);
      return;
    }

    setState(() => _loading = true);
    final result = await _api.post('/api/auth/register', {
      'fullName': _name.text.trim(),
      'age': int.tryParse(_age.text.trim()) ?? 0,
      'gender': _gender,
      'username': _username.text.trim(),
      'email': _registerEmail.text.trim(),
      'password': password,
    });
    if (!mounted) return;
    setState(() => _loading = false);

    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Đăng ký thất bại.', error: true);
      return;
    }

    final verified = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => OtpSheet(email: _registerEmail.text.trim()),
    );
    if (verified == true && mounted) {
      setState(() => _mode = AuthMode.login);
      showAppSnack(context, 'Xác thực thành công. Bạn có thể đăng nhập.');
    }
  }

  Future<void> _forgotPassword() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const ForgotPasswordSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isLogin = _mode == AuthMode.login;

    return Scaffold(
      body: Stack(
        children: [
          const Positioned.fill(child: GridBackground()),
          SafeArea(
            child: CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: ScreenHeader(
                    title: isLogin ? 'Đăng nhập' : 'Tạo tài khoản',
                    subtitle: isLogin
                        ? 'Chào mừng trở lại. Tiếp tục hành trình luyện tập.'
                        : 'Nhập thông tin cá nhân để đăng ký FIT ME.',
                  ),
                ),
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
                    child: Column(
                      children: [
                        AuthSwitch(
                          mode: _mode,
                          onChanged: (mode) => setState(() => _mode = mode),
                        ),
                        const SizedBox(height: 18),
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 220),
                          child: isLogin ? _loginForm() : _registerForm(),
                        ),
                        const Spacer(),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _loginForm() {
    return AppCard(
      key: const ValueKey('login'),
      child: Column(
        children: [
          AppTextField(
            controller: _loginEmail,
            label: 'Email',
            hint: 'Địa chỉ email',
            icon: Icons.mail_outline,
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 12),
          AppTextField(
            controller: _loginPassword,
            label: 'Mật khẩu',
            hint: 'Mật khẩu',
            icon: Icons.lock_outline,
            obscureText: !_showLoginPassword,
            suffix: IconButton(
              onPressed: () =>
                  setState(() => _showLoginPassword = !_showLoginPassword),
              icon: Icon(
                  _showLoginPassword ? Icons.visibility_off : Icons.visibility),
            ),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: _forgotPassword,
              child: const Text(
                'Quên mật khẩu?',
                style: TextStyle(color: AppColors.accentYellow),
              ),
            ),
          ),
          PrimaryButton(
              label: 'Đăng nhập', loading: _loading, onPressed: _login),
        ],
      ),
    );
  }

  Widget _registerForm() {
    return AppCard(
      key: const ValueKey('register'),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: AppTextField(
                  controller: _name,
                  label: 'Họ tên',
                  hint: 'Họ và tên',
                  icon: Icons.person_outline,
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: 88,
                child: AppTextField(
                  controller: _age,
                  label: 'Tuổi',
                  hint: 'Tuổi',
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          GenderSelector(
              value: _gender, onChanged: (v) => setState(() => _gender = v)),
          const SizedBox(height: 12),
          AppTextField(
            controller: _username,
            label: 'Tên đăng nhập',
            hint: 'Tên đăng nhập',
            icon: Icons.badge_outlined,
          ),
          const SizedBox(height: 12),
          AppTextField(
            controller: _registerEmail,
            label: 'Email',
            hint: 'Địa chỉ Email (@gmail.com)',
            icon: Icons.mail_outline,
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 12),
          AppTextField(
            controller: _registerPassword,
            label: 'Mật khẩu',
            hint: 'Từ 8 ký tự, có chữ hoa, thường & số',
            icon: Icons.lock_outline,
            obscureText: !_showRegisterPassword,
            suffix: IconButton(
              onPressed: () => setState(
                  () => _showRegisterPassword = !_showRegisterPassword),
              icon: Icon(_showRegisterPassword
                  ? Icons.visibility_off
                  : Icons.visibility),
            ),
          ),
          const SizedBox(height: 12),
          AppTextField(
            controller: _confirmPassword,
            label: 'Xác nhận mật khẩu',
            hint: 'Nhập lại mật khẩu',
            icon: Icons.lock_reset,
            obscureText: !_showConfirmPassword,
            suffix: IconButton(
              onPressed: () =>
                  setState(() => _showConfirmPassword = !_showConfirmPassword),
              icon: Icon(_showConfirmPassword
                  ? Icons.visibility_off
                  : Icons.visibility),
            ),
          ),
          const SizedBox(height: 18),
          PrimaryButton(
              label: 'Đăng ký', loading: _loading, onPressed: _register),
        ],
      ),
    );
  }
}

class AuthSwitch extends StatelessWidget {
  const AuthSwitch({required this.mode, required this.onChanged, super.key});

  final AuthMode mode;
  final ValueChanged<AuthMode> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 48,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          _SwitchItem(
            label: 'Đăng nhập',
            selected: mode == AuthMode.login,
            onTap: () => onChanged(AuthMode.login),
          ),
          _SwitchItem(
            label: 'Đăng ký',
            selected: mode == AuthMode.register,
            onTap: () => onChanged(AuthMode.register),
          ),
        ],
      ),
    );
  }
}

class _SwitchItem extends StatelessWidget {
  const _SwitchItem({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(9),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppColors.accentPurple : Colors.transparent,
            borderRadius: BorderRadius.circular(9),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: selected ? Colors.white : AppColors.textMuted,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ),
    );
  }
}

class GenderSelector extends StatelessWidget {
  const GenderSelector(
      {required this.value, required this.onChanged, super.key});

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _GenderChip('Nam', Icons.male, value == 'nam', () => onChanged('nam')),
        const SizedBox(width: 8),
        _GenderChip('Nữ', Icons.female, value == 'nu', () => onChanged('nu')),
        const SizedBox(width: 8),
        _GenderChip('Khác', Icons.circle_outlined, value == 'khac',
            () => onChanged('khac')),
      ],
    );
  }
}

class _GenderChip extends StatelessWidget {
  const _GenderChip(this.label, this.icon, this.selected, this.onTap);

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          height: 46,
          decoration: BoxDecoration(
            color: selected
                ? AppColors.accentYellow.withValues(alpha: 0.15)
                : AppColors.bgInput,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: selected ? AppColors.accentYellow : AppColors.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon,
                  size: 17,
                  color:
                      selected ? AppColors.accentYellow : AppColors.textMuted),
              const SizedBox(width: 5),
              Text(
                label,
                style: TextStyle(
                  color:
                      selected ? AppColors.accentYellow : AppColors.textMuted,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class OtpSheet extends StatefulWidget {
  const OtpSheet({required this.email, super.key});

  final String email;

  @override
  State<OtpSheet> createState() => _OtpSheetState();
}

class _OtpSheetState extends State<OtpSheet> {
  final _api = const ApiService();
  final _otp = TextEditingController();
  Timer? _timer;
  int _seconds = 60;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _otp.dispose();
    super.dispose();
  }

  void _startTimer() {
    _timer?.cancel();
    setState(() => _seconds = 60);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_seconds == 0) {
        timer.cancel();
      } else {
        setState(() => _seconds--);
      }
    });
  }

  Future<void> _verify() async {
    if (_otp.text.trim().length != 6) {
      showAppSnack(context, 'Vui lòng nhập đủ 6 số OTP.', error: true);
      return;
    }
    setState(() => _loading = true);
    final result = await _api.post('/api/auth/verify-registration', {
      'email': widget.email,
      'otp': _otp.text.trim(),
    });
    if (!mounted) return;
    setState(() => _loading = false);

    if (result.ok) {
      Navigator.of(context).pop(true);
    } else {
      showAppSnack(context, result.message ?? 'OTP không hợp lệ.', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppSheet(
      title: 'Xác thực Email',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Mã OTP 6 số đã được gửi đến ${widget.email}. Vui lòng kiểm tra hộp thư.',
            style: const TextStyle(color: AppColors.textMuted, height: 1.45),
          ),
          const SizedBox(height: 16),
          AppTextField(
            controller: _otp,
            label: 'OTP',
            hint: 'Nhập mã OTP',
            icon: Icons.password,
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 16),
          PrimaryButton(
              label: 'Xác nhận tài khoản',
              loading: _loading,
              onPressed: _verify),
          TextButton(
            onPressed: _seconds == 0 ? _startTimer : null,
            child:
                Text(_seconds == 0 ? 'Gửi lại mã' : 'Gửi lại (${_seconds}s)'),
          ),
        ],
      ),
    );
  }
}

class ForgotPasswordSheet extends StatefulWidget {
  const ForgotPasswordSheet({super.key});

  @override
  State<ForgotPasswordSheet> createState() => _ForgotPasswordSheetState();
}

class _ForgotPasswordSheetState extends State<ForgotPasswordSheet> {
  final _api = const ApiService();
  final _email = TextEditingController();
  final _otp = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _stepTwo = false;
  bool _loading = false;
  bool _showPassword = false;
  bool _showConfirm = false;

  @override
  void dispose() {
    _email.dispose();
    _otp.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    if (_email.text.trim().isEmpty) return;
    setState(() => _loading = true);
    final result = await _api
        .post('/api/auth/forgot-password', {'email': _email.text.trim()});
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) {
      setState(() => _stepTwo = true);
    } else {
      showAppSnack(context, result.message ?? 'Không gửi được OTP.',
          error: true);
    }
  }

  Future<void> _reset() async {
    final regex = RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$');
    if (_otp.text.trim().length != 6 || !regex.hasMatch(_password.text)) {
      showAppSnack(context, 'OTP hoặc mật khẩu chưa hợp lệ.', error: true);
      return;
    }
    if (_password.text != _confirm.text) {
      showAppSnack(context, 'Mật khẩu xác nhận không khớp.', error: true);
      return;
    }
    setState(() => _loading = true);
    final result = await _api.post('/api/auth/reset-password', {
      'email': _email.text.trim(),
      'otp': _otp.text.trim(),
      'newPassword': _password.text,
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) {
      Navigator.of(context).pop();
      showAppSnack(context, 'Đổi mật khẩu thành công.');
    } else {
      showAppSnack(context, result.message ?? 'Không đổi được mật khẩu.',
          error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppSheet(
      title: _stepTwo ? 'Đặt lại mật khẩu' : 'Khôi phục mật khẩu',
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: _stepTwo ? _stepTwoForm() : _stepOneForm(),
      ),
    );
  }

  Widget _stepOneForm() {
    return Column(
      key: const ValueKey('step1'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Nhập email của bạn để nhận mã OTP đặt lại mật khẩu.',
          style: TextStyle(color: AppColors.textMuted, height: 1.45),
        ),
        const SizedBox(height: 16),
        AppTextField(
          controller: _email,
          label: 'Email',
          hint: 'Nhập địa chỉ email',
          icon: Icons.mail_outline,
        ),
        const SizedBox(height: 16),
        PrimaryButton(
            label: 'Gửi mã OTP', loading: _loading, onPressed: _sendOtp),
      ],
    );
  }

  Widget _stepTwoForm() {
    return Column(
      key: const ValueKey('step2'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(
          controller: _otp,
          label: 'OTP',
          hint: 'Nhập mã OTP',
          icon: Icons.password,
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 12),
        AppTextField(
          controller: _password,
          label: 'Mật khẩu mới',
          hint: 'Từ 8 ký tự, có chữ hoa, thường & số',
          icon: Icons.lock_outline,
          obscureText: !_showPassword,
          suffix: IconButton(
            onPressed: () => setState(() => _showPassword = !_showPassword),
            icon: Icon(_showPassword ? Icons.visibility_off : Icons.visibility),
          ),
        ),
        const SizedBox(height: 12),
        AppTextField(
          controller: _confirm,
          label: 'Xác nhận mật khẩu mới',
          hint: 'Nhập lại mật khẩu',
          icon: Icons.lock_reset,
          obscureText: !_showConfirm,
          suffix: IconButton(
            onPressed: () => setState(() => _showConfirm = !_showConfirm),
            icon: Icon(_showConfirm ? Icons.visibility_off : Icons.visibility),
          ),
        ),
        const SizedBox(height: 16),
        PrimaryButton(
            label: 'Cập nhật mật khẩu', loading: _loading, onPressed: _reset),
      ],
    );
  }
}

class AppSheet extends StatelessWidget {
  const AppSheet({required this.title, required this.child, super.key});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottom),
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        decoration: const BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                Center(
                  child: Container(
                    width: 42,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppColors.border,
                      borderRadius: BorderRadius.circular(99),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          color: AppColors.textMain,
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                child,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

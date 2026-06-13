import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    required this.user,
    required this.onLogout,
    super.key,
  });

  final AppUser user;
  final VoidCallback onLogout;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _api = const ApiService();
  late Future<_ProfileData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_ProfileData> _load() async {
    final results = await Future.wait([
      _api.get('/api/profile/get/${widget.user.id}'),
      _api.get('/api/tcn/overview?userId=${widget.user.id}'),
      _api.get('/api/tcn/weights?userId=${widget.user.id}'),
      _api.get('/api/payment/status/${widget.user.id}'),
    ]);
    final profileBody = _api.mapFrom(results[0].body);
    final overviewBody = _api.mapFrom(results[1].body);
    final weightsBody = _api.mapFrom(results[2].body);
    return _ProfileData(
      profile: _api.mapFrom(profileBody['profile']),
      history: _api.listFrom(profileBody['history']),
      overview: _api.mapFrom(overviewBody['data']),
      weights: _api.listFrom(weightsBody['data']),
      premium: _api.mapFrom(results[3].body),
    );
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _openEdit(Map<String, dynamic> profile) async {
    final updated = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) =>
          EditProfileSheet(userId: widget.user.id, profile: profile),
    );
    if (updated == true) _reload();
  }

  Future<void> _openLog() async {
    final logged = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => LogWeightSheet(userId: widget.user.id),
    );
    if (logged == true) _reload();
  }

  Future<void> _openUpgrade() async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => PaymentSheet(userId: widget.user.id),
    );
    if (changed == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: FutureBuilder<_ProfileData>(
            future: _future,
            builder: (context, snapshot) {
              final data = snapshot.data;
              final profile = data?.profile ?? {};
              final overview = data?.overview ?? {};
              return RefreshIndicator(
                onRefresh: () async => _reload(),
                child: ListView(
                  padding: const EdgeInsets.only(bottom: 24),
                  children: [
                    ScreenHeader(
                      title: profile['fullName']?.toString() ??
                          widget.user.fullName,
                      subtitle: widget.user.isAdmin
                          ? 'Admin'
                          : ((data?.premium['isPremium'] == true ||
                                  widget.user.isPremium)
                              ? 'Premium'
                              : 'Tài khoản thường'),
                      trailing: IconButton.filledTonal(
                        onPressed: widget.onLogout,
                        icon: const Icon(Icons.logout),
                      ),
                    ),
                    if (snapshot.connectionState == ConnectionState.waiting)
                      const Center(
                          child: Padding(
                              padding: EdgeInsets.all(32),
                              child: CircularProgressIndicator()))
                    else ...[
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Row(
                          children: [
                            Expanded(
                                child: _StatCard(
                                    label: 'BMI',
                                    value: '${overview['bmi'] ?? '--'}')),
                            const SizedBox(width: 10),
                            Expanded(
                                child: _StatCard(
                                    label: 'Streak',
                                    value:
                                        '${overview['currentStreak'] ?? 0} ngày')),
                            const SizedBox(width: 10),
                            Expanded(
                                child: _StatCard(
                                    label: 'Buổi tập',
                                    value:
                                        '${overview['workoutsCompleted'] ?? 0}')),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: AppCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Thông tin cơ thể',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      fontSize: 18)),
                              const SizedBox(height: 10),
                              _InfoRow('Tuổi', '${profile['age'] ?? '--'}'),
                              _InfoRow('Cân nặng',
                                  '${profile['weight'] ?? overview['weight'] ?? '--'} kg'),
                              _InfoRow('Chiều cao',
                                  '${profile['height'] ?? overview['height'] ?? '--'} cm'),
                              _InfoRow(
                                  'Mục tiêu', '${profile['goalType'] ?? '--'}'),
                              const SizedBox(height: 14),
                              Row(
                                children: [
                                  Expanded(
                                      child: PrimaryButton(
                                          label: 'Sửa hồ sơ',
                                          onPressed: () => _openEdit(profile))),
                                  const SizedBox(width: 10),
                                  Expanded(
                                      child: PrimaryButton(
                                          label: 'Ghi log',
                                          onPressed: _openLog)),
                                ],
                              ),
                              if (!(data?.premium['isPremium'] == true ||
                                  widget.user.isPremium)) ...[
                                const SizedBox(height: 10),
                                PrimaryButton(
                                  label: 'Nâng cấp Premium',
                                  onPressed: _openUpgrade,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      _WeightsList(items: data?.weights ?? const []),
                      const SizedBox(height: 14),
                      _HistoryList(items: data?.history ?? const []),
                    ],
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class PaymentSheet extends StatefulWidget {
  const PaymentSheet({required this.userId, super.key});

  final String userId;

  @override
  State<PaymentSheet> createState() => _PaymentSheetState();
}

class _PaymentSheetState extends State<PaymentSheet> {
  final _api = const ApiService();
  String _plan = 'vip_1month';
  Map<String, dynamic>? _payment;
  bool _loading = false;

  Future<void> _create() async {
    setState(() => _loading = true);
    final result = await _api.post('/api/payment/create', {
      'userId': widget.userId,
      'planType': _plan,
      'plan_type': _plan,
    });
    if (!mounted) return;
    setState(() {
      _payment = _api.mapFrom(result.body);
      _loading = false;
    });
    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Không tạo được thanh toán.',
          error: true);
    }
  }

  Future<void> _check() async {
    final transfer = _payment?['transfer_content']?.toString();
    if (transfer == null || transfer.isEmpty) return;
    setState(() => _loading = true);
    final result = await _api.get(
        '/api/payment/check?transfer_content=$transfer&userId=${widget.userId}');
    if (!mounted) return;
    setState(() => _loading = false);
    final body = _api.mapFrom(result.body);
    if (body['status'] == 'paid') {
      Navigator.of(context).pop(true);
      showAppSnack(context, 'Premium đã được kích hoạt.');
    } else {
      showAppSnack(context, 'Thanh toán đang chờ xác nhận.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return _Sheet(
      title: 'Nâng cấp Premium',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'vip_1month', label: Text('1 tháng')),
              ButtonSegment(value: 'vip_3month', label: Text('3 tháng')),
            ],
            selected: {_plan},
            onSelectionChanged: (value) => setState(() => _plan = value.first),
          ),
          const SizedBox(height: 14),
          PrimaryButton(
            label: 'Tạo mã thanh toán',
            loading: _loading,
            onPressed: _create,
          ),
          if (_payment != null) ...[
            const SizedBox(height: 16),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _InfoRow('Ngân hàng', '${_payment!['bank_code'] ?? '--'}'),
                  _InfoRow(
                      'Số tài khoản', '${_payment!['account_number'] ?? '--'}'),
                  _InfoRow('Số tiền', '${_payment!['amount'] ?? '--'}đ'),
                  _InfoRow(
                      'Nội dung', '${_payment!['transfer_content'] ?? '--'}'),
                  const SizedBox(height: 12),
                  if ((_payment!['qr_url'] ?? '').toString().isNotEmpty)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        _payment!['qr_url'].toString(),
                        height: 220,
                        fit: BoxFit.contain,
                        errorBuilder: (_, __, ___) => const Text(
                          'Không tải được QR. Hãy chuyển khoản theo thông tin trên.',
                          style: TextStyle(color: AppColors.textMuted),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Kiểm tra thanh toán',
              loading: _loading,
              onPressed: _check,
            ),
          ],
        ],
      ),
    );
  }
}

class _ProfileData {
  const _ProfileData({
    required this.profile,
    required this.history,
    required this.overview,
    required this.weights,
    required this.premium,
  });

  final Map<String, dynamic> profile;
  final List<Map<String, dynamic>> history;
  final Map<String, dynamic> overview;
  final List<Map<String, dynamic>> weights;
  final Map<String, dynamic> premium;
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          Text(value,
              style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                  color: AppColors.accentYellow)),
          const SizedBox(height: 4),
          Text(label,
              style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(
              child: Text(label,
                  style: const TextStyle(color: AppColors.textMuted))),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _WeightsList extends StatelessWidget {
  const _WeightsList({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Mức tạ đề xuất',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
            const SizedBox(height: 10),
            ...items.map((item) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text((item['muscle'] ?? '').toString()),
                  subtitle: Text((item['comment'] ?? '').toString()),
                  trailing: Text('${item['weight'] ?? '--'} kg',
                      style: const TextStyle(
                          color: AppColors.accentYellow,
                          fontWeight: FontWeight.w900)),
                )),
          ],
        ),
      ),
    );
  }
}

class _HistoryList extends StatelessWidget {
  const _HistoryList({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Lịch sử cân nặng',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
            const SizedBox(height: 10),
            if (items.isEmpty)
              const Text('Chưa có log.',
                  style: TextStyle(color: AppColors.textMuted))
            else
              ...items.reversed.take(6).map((item) => _InfoRow(
                    (item['date'] ?? '').toString(),
                    '${item['weight'] ?? '--'} kg',
                  )),
          ],
        ),
      ),
    );
  }
}

class EditProfileSheet extends StatefulWidget {
  const EditProfileSheet({
    required this.userId,
    required this.profile,
    super.key,
  });

  final String userId;
  final Map<String, dynamic> profile;

  @override
  State<EditProfileSheet> createState() => _EditProfileSheetState();
}

class _EditProfileSheetState extends State<EditProfileSheet> {
  final _api = const ApiService();
  late final TextEditingController _name;
  late final TextEditingController _age;
  late final TextEditingController _weight;
  late final TextEditingController _height;
  late final TextEditingController _goalWeight;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(
        text: widget.profile['fullName']?.toString() ?? '');
    _age = TextEditingController(text: widget.profile['age']?.toString() ?? '');
    _weight =
        TextEditingController(text: widget.profile['weight']?.toString() ?? '');
    _height =
        TextEditingController(text: widget.profile['height']?.toString() ?? '');
    _goalWeight = TextEditingController(
        text: widget.profile['goalWeight']?.toString() ?? '');
  }

  @override
  void dispose() {
    _name.dispose();
    _age.dispose();
    _weight.dispose();
    _height.dispose();
    _goalWeight.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    final result = await _api.put('/api/profile/update/${widget.userId}', {
      'fullName': _name.text.trim(),
      'age': int.tryParse(_age.text.trim()) ?? 0,
      'gender': widget.profile['gender'] ?? 'khac',
      'weight': double.tryParse(_weight.text.trim()) ?? 0,
      'height': double.tryParse(_height.text.trim()) ?? 0,
      'goalWeight': double.tryParse(_goalWeight.text.trim()) ?? 0,
      'level': widget.profile['level'] ?? 'beginner',
      'goalType': widget.profile['goalType'] ?? 'general',
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) Navigator.of(context).pop(true);
    showAppSnack(context, result.message ?? 'Đã cập nhật hồ sơ.',
        error: !result.ok);
  }

  @override
  Widget build(BuildContext context) {
    return _Sheet(
      title: 'Sửa hồ sơ',
      child: Column(
        children: [
          AppTextField(controller: _name, label: 'Họ tên', hint: 'Họ tên'),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                  child: AppTextField(
                      controller: _age,
                      label: 'Tuổi',
                      hint: 'Tuổi',
                      keyboardType: TextInputType.number)),
              const SizedBox(width: 10),
              Expanded(
                  child: AppTextField(
                      controller: _height,
                      label: 'Chiều cao',
                      hint: 'cm',
                      keyboardType: TextInputType.number)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                  child: AppTextField(
                      controller: _weight,
                      label: 'Cân nặng',
                      hint: 'kg',
                      keyboardType: TextInputType.number)),
              const SizedBox(width: 10),
              Expanded(
                  child: AppTextField(
                      controller: _goalWeight,
                      label: 'Mục tiêu',
                      hint: 'kg',
                      keyboardType: TextInputType.number)),
            ],
          ),
          const SizedBox(height: 16),
          PrimaryButton(label: 'Lưu', loading: _loading, onPressed: _save),
        ],
      ),
    );
  }
}

class LogWeightSheet extends StatefulWidget {
  const LogWeightSheet({required this.userId, super.key});

  final String userId;

  @override
  State<LogWeightSheet> createState() => _LogWeightSheetState();
}

class _LogWeightSheetState extends State<LogWeightSheet> {
  final _api = const ApiService();
  final _weight = TextEditingController();
  final _note = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _weight.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    final result = await _api.post('/api/profile/log/${widget.userId}', {
      'weight': double.tryParse(_weight.text.trim()) ?? 0,
      'note': _note.text.trim(),
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) Navigator.of(context).pop(true);
    showAppSnack(context, result.message ?? 'Đã lưu nhật ký.',
        error: !result.ok);
  }

  @override
  Widget build(BuildContext context) {
    return _Sheet(
      title: 'Ghi log hôm nay',
      child: Column(
        children: [
          AppTextField(
              controller: _weight,
              label: 'Cân nặng',
              hint: 'kg',
              keyboardType: TextInputType.number),
          const SizedBox(height: 12),
          AppTextField(
              controller: _note,
              label: 'Ghi chú',
              hint: 'Cảm nhận hôm nay',
              maxLines: 3),
          const SizedBox(height: 16),
          PrimaryButton(label: 'Lưu log', loading: _loading, onPressed: _save),
        ],
      ),
    );
  }
}

class _Sheet extends StatelessWidget {
  const _Sheet({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        decoration: const BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w900)),
                const SizedBox(height: 16),
                child,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

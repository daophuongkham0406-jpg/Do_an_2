import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    required this.user,
    required this.onLogout,
    required this.onOpenPlan,
    super.key,
  });

  final AppUser user;
  final VoidCallback onLogout;
  final VoidCallback onOpenPlan;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _api = const ApiService();
  late Future<_ProfileData> _future;
  String? _savingMuscle;

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
      _api.get('/api/tcn/radar?userId=${widget.user.id}'),
      _api.get('/api/tcn/weight-chart?userId=${widget.user.id}'),
      _api.get('/api/plans/get-active-plan?userId=${widget.user.id}'),
    ]);

    final profileBody = _api.mapFrom(results[0].body);
    final overviewBody = _api.mapFrom(results[1].body);
    final weightsBody = _api.mapFrom(results[2].body);
    final radarBody = _api.mapFrom(results[4].body);
    final chartBody = _api.mapFrom(results[5].body);
    final planBody = _api.mapFrom(results[6].body);

    return _ProfileData(
      profile: _api.mapFrom(profileBody['profile']),
      history: _api.listFrom(profileBody['history']),
      overview: _api.mapFrom(overviewBody['data']),
      weights: _api.listFrom(weightsBody['data']),
      premium: _api.mapFrom(results[3].body),
      radar: _numbersFrom(radarBody['data']),
      weightChart: _api.mapFrom(chartBody['data']),
      activePlan: _api.mapFrom(planBody['plan']),
    );
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _refresh() async {
    _reload();
    await _future;
  }

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

  Future<void> _openAllWorkouts(List<Map<String, dynamic>> items) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _WorkoutHistorySheet(items: items),
    );
  }

  Future<void> _adjustWeight(Map<String, dynamic> item, num delta) async {
    final muscle = item['muscle']?.toString() ?? '';
    if (muscle.isEmpty || _savingMuscle != null) return;
    final current = _num(item['weight']);
    final next = math.max(1.0, current + delta);
    setState(() => _savingMuscle = muscle);
    final result = await _api.post('/api/tcn/weights/update', {
      'userId': widget.user.id,
      'muscle': muscle,
      'weight': next,
    });
    if (!mounted) return;
    setState(() => _savingMuscle = null);
    showAppSnack(
      context,
      result.ok ? 'Đã cập nhật mức tạ $muscle.' : 'Không lưu được mức tạ.',
      error: !result.ok,
    );
    if (result.ok) _reload();
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
              if (snapshot.connectionState == ConnectionState.waiting &&
                  data == null) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError && data == null) {
                return _ErrorState(onRetry: _reload);
              }

              final safeData = data ?? _ProfileData.empty();
              final profile = safeData.profile;
              final overview = safeData.overview;
              final premium = safeData.premium['isPremium'] == true;
              final allWorkouts = _mapsFrom(overview['allWorkouts']);

              return RefreshIndicator(
                onRefresh: _refresh,
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
                  children: [
                    _ProfileHero(
                      profile: profile,
                      overview: overview,
                      premium: premium,
                      user: widget.user,
                      onEdit: () => _openEdit(profile),
                      onLog: _openLog,
                      onUpgrade: _openUpgrade,
                      onLogout: widget.onLogout,
                    ),
                    const SizedBox(height: 14),
                    _MetricStrip(overview: overview),
                    const SizedBox(height: 14),
                    _ActivePlanCard(
                      plan: safeData.activePlan,
                      onOpenPlan: widget.onOpenPlan,
                    ),
                    const SizedBox(height: 14),
                    _BodyStatsCard(profile: profile, overview: overview),
                    const SizedBox(height: 14),
                    _WeightChartCard(
                      chart: safeData.weightChart,
                      history: safeData.history,
                      onLog: _openLog,
                    ),
                    const SizedBox(height: 14),
                    _FrequencyCard(values: _numbersFrom(overview['freqData'])),
                    const SizedBox(height: 14),
                    _RadarCard(values: safeData.radar),
                    const SizedBox(height: 14),
                    _WeightsCard(
                      items: safeData.weights,
                      savingMuscle: _savingMuscle,
                      onAdjust: _adjustWeight,
                    ),
                    const SizedBox(height: 14),
                    _RecentWorkoutsCard(
                      recent: _mapsFrom(overview['recentWorkouts']),
                      all: allWorkouts,
                      onViewAll: () => _openAllWorkouts(allWorkouts),
                    ),
                    if (safeData.history.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      _WeightLogCard(items: safeData.history),
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
      '/api/payment/check?transfer_content=$transfer&userId=${widget.userId}',
    );
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
    final price = _plan == 'vip_1month' ? '50.000đ' : '120.000đ';
    return _Sheet(
      title: 'Nâng cấp Premium',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: 'vip_1month',
                icon: Icon(Icons.calendar_month_outlined),
                label: Text('1 tháng'),
              ),
              ButtonSegment(
                value: 'vip_3month',
                icon: Icon(Icons.workspace_premium_outlined),
                label: Text('3 tháng'),
              ),
            ],
            selected: {_plan},
            onSelectionChanged: (value) => setState(() => _plan = value.first),
          ),
          const SizedBox(height: 12),
          _InfoTile(label: 'Gói đang chọn', value: price, highlight: true),
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
                  _InfoRow('Số tiền', _money(_payment!['amount'])),
                  _InfoRow(
                      'Nội dung', '${_payment!['transfer_content'] ?? '--'}'),
                  const SizedBox(height: 12),
                  if ((_payment!['qr_url'] ?? '').toString().isNotEmpty)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
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
      title: 'Chỉnh sửa hồ sơ',
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
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: AppTextField(
                  controller: _height,
                  label: 'Chiều cao',
                  hint: 'cm',
                  keyboardType: TextInputType.number,
                ),
              ),
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
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: AppTextField(
                  controller: _goalWeight,
                  label: 'Mục tiêu',
                  hint: 'kg',
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          PrimaryButton(
              label: 'Lưu thay đổi', loading: _loading, onPressed: _save),
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
      title: 'Cập nhật chỉ số',
      child: Column(
        children: [
          AppTextField(
            controller: _weight,
            label: 'Cân nặng hôm nay',
            hint: 'kg',
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          AppTextField(
            controller: _note,
            label: 'Ghi chú',
            hint: 'Cảm nhận sau buổi tập',
            maxLines: 3,
          ),
          const SizedBox(height: 16),
          PrimaryButton(
              label: 'Lưu chỉ số', loading: _loading, onPressed: _save),
        ],
      ),
    );
  }
}

class _ProfileHero extends StatelessWidget {
  const _ProfileHero({
    required this.profile,
    required this.overview,
    required this.premium,
    required this.user,
    required this.onEdit,
    required this.onLog,
    required this.onUpgrade,
    required this.onLogout,
  });

  final Map<String, dynamic> profile;
  final Map<String, dynamic> overview;
  final bool premium;
  final AppUser user;
  final VoidCallback onEdit;
  final VoidCallback onLog;
  final VoidCallback onUpgrade;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final name = _text(
      profile['fullName'] ?? overview['fullName'] ?? user.fullName,
      fallback: 'FIT ME User',
    );
    final avatarUrl = _text(profile['avatarUrl'] ?? profile['avatar']);

    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Avatar(name: name, imageUrl: avatarUrl),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 23,
                              height: 1.05,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        IconButton.filledTonal(
                          tooltip: 'Đăng xuất',
                          onPressed: onLogout,
                          icon: const Icon(Icons.logout, size: 20),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _StatusChip(
                          icon: premium
                              ? Icons.workspace_premium
                              : Icons.person_outline,
                          label: premium ? 'Premium' : 'Tài khoản thường',
                          color: premium
                              ? AppColors.accentYellow
                              : AppColors.textMuted,
                        ),
                        _StatusChip(
                          icon: Icons.local_fire_department_outlined,
                          label: '${_int(overview['currentStreak'])} ngày',
                          color: AppColors.success,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetaChip(
                Icons.cake_outlined,
                '${_text(profile['age'], fallback: '--')} tuổi',
              ),
              _MetaChip(
                Icons.monitor_weight_outlined,
                '${_compactNum(profile['weight'] ?? overview['weight'])} kg',
              ),
              _MetaChip(
                Icons.height,
                '${_compactNum(profile['height'] ?? overview['height'])} cm',
              ),
              _MetaChip(Icons.speed, 'BMI ${_compactNum(overview['bmi'])}'),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: const Text('Chỉnh sửa'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onLog,
                  icon: const Icon(Icons.add_chart_outlined, size: 18),
                  label: const Text('Cập nhật'),
                ),
              ),
            ],
          ),
          if (!premium) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onUpgrade,
                icon: const Icon(Icons.workspace_premium_outlined, size: 18),
                label: const Text('Nâng cấp Premium'),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.accentYellow,
                  foregroundColor: Colors.black,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MetricStrip extends StatelessWidget {
  const _MetricStrip({required this.overview});

  final Map<String, dynamic> overview;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _MetricCard(
            icon: Icons.fitness_center,
            label: 'Buổi tập',
            value: '${_int(overview['workoutsCompleted'])}',
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetricCard(
            icon: Icons.route,
            label: 'Lộ trình',
            value: '${_int(overview['routinesCompleted'])}',
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetricCard(
            icon: Icons.trending_down,
            label: 'Biến động',
            value: '${_compactNum(overview['weightChange'])} kg',
          ),
        ),
      ],
    );
  }
}

class _ActivePlanCard extends StatelessWidget {
  const _ActivePlanCard({required this.plan, required this.onOpenPlan});

  final Map<String, dynamic> plan;
  final VoidCallback onOpenPlan;

  @override
  Widget build(BuildContext context) {
    if (plan.isEmpty) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _CardTitle(
                icon: Icons.route_outlined, title: 'Lộ trình hiện tại'),
            const SizedBox(height: 10),
            const Text(
              'Bạn chưa áp dụng lộ trình nào.',
              style: TextStyle(color: AppColors.textMuted),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onOpenPlan,
                icon: const Icon(Icons.add_road_outlined),
                label: const Text('Tạo lộ trình'),
              ),
            ),
          ],
        ),
      );
    }

    final planData = _mapFrom(plan['plan_data']);
    final progress = _mapsFrom(plan['daily_progress']);
    final days = _mapsFrom(planData['days']);
    final title = _text(
      planData['plan_name'] ?? planData['title'],
      fallback: 'Lộ trình đang áp dụng',
    );
    final done = progress
        .where((day) => day['day_done'] == true || day['completed'] == true)
        .length;
    final total = progress.isNotEmpty ? progress.length : days.length;
    final ratio = total <= 0 ? 0.0 : done / total;
    final nextDay = progress.indexWhere(
      (day) => day['day_done'] != true && day['completed'] != true,
    );

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(
              icon: Icons.route_outlined, title: 'Lộ trình hiện tại'),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: ratio.clamp(0, 1),
            minHeight: 9,
            borderRadius: BorderRadius.circular(8),
            backgroundColor: AppColors.bgInput,
            color: AppColors.accentYellow,
          ),
          const SizedBox(height: 8),
          Text(
            '$done/$total ngày hoàn thành'
            '${nextDay >= 0 ? ' • Tiếp theo ngày ${nextDay + 1}' : ''}',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: onOpenPlan,
              icon: const Icon(Icons.settings_outlined, size: 18),
              label: const Text('Quản lý lộ trình'),
            ),
          ),
        ],
      ),
    );
  }
}

class _BodyStatsCard extends StatelessWidget {
  const _BodyStatsCard({required this.profile, required this.overview});

  final Map<String, dynamic> profile;
  final Map<String, dynamic> overview;

  @override
  Widget build(BuildContext context) {
    final bmi = _num(overview['bmi']);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(
              icon: Icons.analytics_outlined, title: 'Chỉ số cơ thể'),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _InfoTile(
                  label: 'Cân nặng',
                  value:
                      '${_compactNum(profile['weight'] ?? overview['weight'])} kg',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _InfoTile(
                  label: 'Chiều cao',
                  value:
                      '${_compactNum(profile['height'] ?? overview['height'])} cm',
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _InfoTile(
                  label: 'BMI',
                  value: _compactNum(bmi),
                  highlight: true,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _InfoTile(
                  label: 'Cơ ước tính',
                  value: '${_compactNum(overview['musclePct'])}%',
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _BmiGauge(value: bmi),
        ],
      ),
    );
  }
}

class _WeightChartCard extends StatelessWidget {
  const _WeightChartCard({
    required this.chart,
    required this.history,
    required this.onLog,
  });

  final Map<String, dynamic> chart;
  final List<Map<String, dynamic>> history;
  final VoidCallback onLog;

  @override
  Widget build(BuildContext context) {
    final weights = _numbersFrom(chart['weights']);
    final labels = _stringsFrom(chart['labels']);
    final goal = _num(chart['goal_weight']);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: _CardTitle(
                    icon: Icons.show_chart, title: 'Theo dõi cân nặng'),
              ),
              TextButton.icon(
                onPressed: onLog,
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Log'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (weights.length < 2)
            const _EmptyBox(text: 'Chưa đủ dữ liệu để vẽ biểu đồ.')
          else
            SizedBox(
              height: 180,
              child: CustomPaint(
                painter: _LineChartPainter(
                  weights: weights,
                  labels: labels,
                  goal: goal,
                ),
                child: const SizedBox.expand(),
              ),
            ),
          if (history.isNotEmpty) ...[
            const SizedBox(height: 12),
            _InfoRow('Lần gần nhất', '${history.last['weight'] ?? '--'} kg'),
          ],
        ],
      ),
    );
  }
}

class _FrequencyCard extends StatelessWidget {
  const _FrequencyCard({required this.values});

  final List<double> values;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(icon: Icons.bar_chart, title: 'Tần suất 8 tuần'),
          const SizedBox(height: 12),
          SizedBox(
            height: 150,
            child: CustomPaint(
              painter: _BarChartPainter(values: values),
              child: const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarCard extends StatelessWidget {
  const _RadarCard({required this.values});

  final List<double> values;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(
              icon: Icons.radar_outlined, title: 'Phát triển nhóm cơ'),
          const SizedBox(height: 12),
          SizedBox(
            height: 230,
            child: CustomPaint(
              painter: _RadarPainter(values: values),
              child: const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}

class _WeightsCard extends StatelessWidget {
  const _WeightsCard({
    required this.items,
    required this.savingMuscle,
    required this.onAdjust,
  });

  final List<Map<String, dynamic>> items;
  final String? savingMuscle;
  final Future<void> Function(Map<String, dynamic> item, num delta) onAdjust;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(icon: Icons.fitness_center, title: 'Mức tạ của bạn'),
          const SizedBox(height: 10),
          if (items.isEmpty)
            const _EmptyBox(text: 'Chưa có dữ liệu mức tạ.')
          else
            ...items.map((item) {
              final muscle = item['muscle']?.toString() ?? '';
              final saving = savingMuscle == muscle;
              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.bgInput,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: item['is_upgrade'] == true
                        ? AppColors.accentYellow.withValues(alpha: 0.55)
                        : AppColors.border,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            muscle,
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _text(item['comment'],
                                fallback: 'Mức tạ khởi điểm.'),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 12,
                              height: 1.35,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _TinyIconButton(
                          icon: Icons.remove,
                          tooltip: 'Giảm tạ',
                          disabled: saving,
                          onPressed: () => onAdjust(item, -1),
                        ),
                        SizedBox(
                          width: 62,
                          child: Center(
                            child: saving
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : Text(
                                    '${_compactNum(item['weight'])} kg',
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      color: AppColors.accentYellow,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                          ),
                        ),
                        _TinyIconButton(
                          icon: Icons.add,
                          tooltip: 'Tăng tạ',
                          disabled: saving,
                          onPressed: () => onAdjust(item, 1),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}

class _RecentWorkoutsCard extends StatelessWidget {
  const _RecentWorkoutsCard({
    required this.recent,
    required this.all,
    required this.onViewAll,
  });

  final List<Map<String, dynamic>> recent;
  final List<Map<String, dynamic>> all;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child:
                    _CardTitle(icon: Icons.history, title: 'Buổi tập gần đây'),
              ),
              TextButton(
                onPressed: all.isEmpty ? null : onViewAll,
                child: const Text('Xem tất cả'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (recent.isEmpty)
            const _EmptyBox(text: 'Chưa có buổi tập hoàn thành.')
          else
            ...recent.map((item) => _WorkoutRow(item: item)),
        ],
      ),
    );
  }
}

class _WeightLogCard extends StatelessWidget {
  const _WeightLogCard({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle(
              icon: Icons.list_alt_outlined, title: 'Lịch sử cân nặng'),
          const SizedBox(height: 10),
          ...items.reversed.take(6).map(
                (item) => _InfoRow(
                  _prettyDate(item['date']),
                  '${item['weight'] ?? '--'} kg',
                ),
              ),
        ],
      ),
    );
  }
}

class _WorkoutHistorySheet extends StatelessWidget {
  const _WorkoutHistorySheet({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return _Sheet(
      title: 'Tất cả buổi tập',
      child: Column(
        children: [
          if (items.isEmpty)
            const _EmptyBox(text: 'Chưa có lịch sử tập luyện.')
          else
            ...items.map((item) => _WorkoutRow(item: item)),
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
    required this.radar,
    required this.weightChart,
    required this.activePlan,
  });

  factory _ProfileData.empty() => const _ProfileData(
        profile: {},
        history: [],
        overview: {},
        weights: [],
        premium: {},
        radar: [],
        weightChart: {},
        activePlan: {},
      );

  final Map<String, dynamic> profile;
  final List<Map<String, dynamic>> history;
  final Map<String, dynamic> overview;
  final List<Map<String, dynamic>> weights;
  final Map<String, dynamic> premium;
  final List<double> radar;
  final Map<String, dynamic> weightChart;
  final Map<String, dynamic> activePlan;
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.name, required this.imageUrl});

  final String name;
  final String imageUrl;

  @override
  Widget build(BuildContext context) {
    final letter = name.trim().isEmpty ? 'F' : name.trim()[0].toUpperCase();
    final image = imageUrl.isEmpty ? null : NetworkImage(imageUrl);
    return Container(
      width: 72,
      height: 72,
      decoration: BoxDecoration(
        color: AppColors.accentPurple.withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
        image: image == null
            ? null
            : DecorationImage(image: image, fit: BoxFit.cover),
      ),
      alignment: Alignment.center,
      child: image == null
          ? Text(
              letter,
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900),
            )
          : null,
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: AppColors.accentYellow),
          const SizedBox(height: 10),
          FittedBox(
            alignment: Alignment.centerLeft,
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
            ),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _CardTitle extends StatelessWidget {
  const _CardTitle({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 20, color: AppColors.accentYellow),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            title,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17),
          ),
        ),
      ],
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.32)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.icon, this.label);

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.textMuted),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.label,
    required this.value,
    this.highlight = false,
  });

  final String label;
  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: 5),
          FittedBox(
            alignment: Alignment.centerLeft,
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: TextStyle(
                color: highlight ? AppColors.accentYellow : AppColors.textMain,
                fontSize: 18,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BmiGauge extends StatelessWidget {
  const _BmiGauge({required this.value});

  final double value;

  @override
  Widget build(BuildContext context) {
    final position = value <= 0 ? 0.0 : ((value - 14) / 24).clamp(0.0, 1.0);
    final label = value <= 0
        ? 'Chưa có dữ liệu'
        : value < 18.5
            ? 'Thiếu cân'
            : value < 25
                ? 'Cân đối'
                : value < 30
                    ? 'Thừa cân'
                    : 'Cần kiểm soát';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(label,
                  style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
            Text(
              value <= 0 ? '--' : _compactNum(value),
              style: const TextStyle(
                color: AppColors.accentYellow,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        LayoutBuilder(
          builder: (context, constraints) {
            return SizedBox(
              height: 18,
              child: Stack(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: _GaugeSegment(
                          AppColors.accentPurple.withValues(alpha: 0.78),
                        ),
                      ),
                      const Expanded(child: _GaugeSegment(AppColors.success)),
                      const Expanded(
                          child: _GaugeSegment(AppColors.accentYellow)),
                      const Expanded(child: _GaugeSegment(AppColors.danger)),
                    ],
                  ),
                  Positioned(
                    left: (constraints.maxWidth - 10) * position,
                    top: 0,
                    bottom: 0,
                    child: Container(
                      width: 10,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.black, width: 1.2),
                      ),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _GaugeSegment extends StatelessWidget {
  const _GaugeSegment(this.color);

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 12,
      margin: const EdgeInsets.only(right: 4),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}

class _WorkoutRow extends StatelessWidget {
  const _WorkoutRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: AppColors.success, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _text(item['name'], fallback: 'Buổi tập'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 3),
                Text(
                  '${_text(item['date'], fallback: '--')} • ${_text(item['vol'], fallback: '--')}',
                  style:
                      const TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TinyIconButton extends StatelessWidget {
  const _TinyIconButton({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
    this.disabled = false,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;
  final bool disabled;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 34,
      height: 34,
      child: IconButton.filledTonal(
        padding: EdgeInsets.zero,
        tooltip: tooltip,
        onPressed: disabled ? null : onPressed,
        icon: Icon(icon, size: 18),
      ),
    );
  }
}

class _EmptyBox extends StatelessWidget {
  const _EmptyBox({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(text, style: const TextStyle(color: AppColors.textMuted)),
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
            child:
                Text(label, style: const TextStyle(color: AppColors.textMuted)),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
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
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.9,
        ),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        decoration: const BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 44,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: AppColors.border,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
                Text(
                  title,
                  style: const TextStyle(
                      fontSize: 22, fontWeight: FontWeight.w900),
                ),
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

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: AppCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined,
                  color: AppColors.danger, size: 34),
              const SizedBox(height: 10),
              const Text(
                'Không tải được trang cá nhân.',
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 12),
              PrimaryButton(label: 'Thử lại', onPressed: onRetry),
            ],
          ),
        ),
      ),
    );
  }
}

class _LineChartPainter extends CustomPainter {
  const _LineChartPainter({
    required this.weights,
    required this.labels,
    required this.goal,
  });

  final List<double> weights;
  final List<String> labels;
  final double goal;

  @override
  void paint(Canvas canvas, Size size) {
    final chart = Rect.fromLTWH(6, 8, size.width - 12, size.height - 32);
    final values = [...weights, if (goal > 0) goal];
    final minVal = values.reduce(math.min) - 2;
    final maxVal = values.reduce(math.max) + 2;
    final range = math.max(1.0, maxVal - minVal);
    final gridPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.08)
      ..strokeWidth = 1;

    for (var i = 0; i < 4; i++) {
      final y = chart.top + chart.height * i / 3;
      canvas.drawLine(Offset(chart.left, y), Offset(chart.right, y), gridPaint);
    }

    if (goal > 0) {
      final y = chart.bottom - ((goal - minVal) / range) * chart.height;
      final paint = Paint()
        ..color = AppColors.accentYellow.withValues(alpha: 0.45)
        ..strokeWidth = 1.4;
      canvas.drawLine(Offset(chart.left, y), Offset(chart.right, y), paint);
    }

    final points = <Offset>[];
    for (var i = 0; i < weights.length; i++) {
      final x = chart.left +
          (weights.length == 1 ? 0 : chart.width * i / (weights.length - 1));
      final y = chart.bottom - ((weights[i] - minVal) / range) * chart.height;
      points.add(Offset(x, y));
    }

    final linePaint = Paint()
      ..color = AppColors.accentPurple
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, linePaint);

    final dotPaint = Paint()..color = AppColors.accentYellow;
    for (final p in points) {
      canvas.drawCircle(p, 4, dotPaint);
    }

    final label = labels.isEmpty ? '' : labels.last;
    _paintText(
      canvas,
      label.length > 10 ? label.substring(0, 10) : label,
      Offset(chart.right - 72, chart.bottom + 10),
      AppColors.textMuted,
      11,
    );
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) =>
      oldDelegate.weights != weights || oldDelegate.goal != goal;
}

class _BarChartPainter extends CustomPainter {
  const _BarChartPainter({required this.values});

  final List<double> values;

  @override
  void paint(Canvas canvas, Size size) {
    final data = values.isEmpty ? List<double>.filled(8, 0) : values;
    final maxVal = math.max(1.0, data.reduce(math.max));
    final barWidth = (size.width - 14 * (data.length - 1)) / data.length;
    final base = size.height - 24;
    for (var i = 0; i < data.length; i++) {
      final h = (base - 12) * (data[i] / maxVal);
      final left = i * (barWidth + 14);
      final rect = RRect.fromRectAndRadius(
        Rect.fromLTWH(left, base - h, barWidth, h.clamp(4, base)),
        const Radius.circular(8),
      );
      final color = Color.lerp(
        AppColors.accentPurple,
        AppColors.accentYellow,
        i / math.max(1, data.length - 1),
      )!;
      canvas.drawRRect(rect, Paint()..color = color);
      _paintText(canvas, 'T${i + 1}', Offset(left + 1, base + 8),
          AppColors.textMuted, 10);
    }
  }

  @override
  bool shouldRepaint(covariant _BarChartPainter oldDelegate) =>
      oldDelegate.values != values;
}

class _RadarPainter extends CustomPainter {
  const _RadarPainter({required this.values});

  final List<double> values;
  static const labels = ['Ngực', 'Lưng', 'Chân', 'Vai', 'Tay', 'Bụng'];

  @override
  void paint(Canvas canvas, Size size) {
    final data = List<double>.generate(
      6,
      (i) => i < values.length ? values[i].clamp(0, 10).toDouble() : 0,
    );
    final center = Offset(size.width / 2, size.height / 2 + 4);
    final radius = math.min(size.width, size.height) * 0.32;
    final gridPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.09)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    for (var ring = 1; ring <= 4; ring++) {
      final path = Path();
      for (var i = 0; i < 6; i++) {
        final p = _radarPoint(center, radius * ring / 4, i, 6);
        if (i == 0) {
          path.moveTo(p.dx, p.dy);
        } else {
          path.lineTo(p.dx, p.dy);
        }
      }
      path.close();
      canvas.drawPath(path, gridPaint);
    }

    for (var i = 0; i < 6; i++) {
      final p = _radarPoint(center, radius, i, 6);
      canvas.drawLine(center, p, gridPaint);
      final labelPoint = _radarPoint(center, radius + 26, i, 6);
      _paintText(
        canvas,
        labels[i],
        labelPoint - const Offset(15, 7),
        AppColors.textMuted,
        11,
      );
    }

    final path = Path();
    for (var i = 0; i < 6; i++) {
      final p = _radarPoint(center, radius * data[i] / 10, i, 6);
      if (i == 0) {
        path.moveTo(p.dx, p.dy);
      } else {
        path.lineTo(p.dx, p.dy);
      }
    }
    path.close();
    canvas.drawPath(
      path,
      Paint()
        ..color = AppColors.accentPurple.withValues(alpha: 0.28)
        ..style = PaintingStyle.fill,
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = AppColors.accentYellow
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2,
    );
  }

  Offset _radarPoint(Offset center, double radius, int index, int total) {
    final angle = -math.pi / 2 + math.pi * 2 * index / total;
    return Offset(
      center.dx + math.cos(angle) * radius,
      center.dy + math.sin(angle) * radius,
    );
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) =>
      oldDelegate.values != values;
}

void _paintText(
  Canvas canvas,
  String text,
  Offset offset,
  Color color,
  double fontSize,
) {
  final painter = TextPainter(
    text: TextSpan(
      text: text,
      style: TextStyle(
        color: color,
        fontSize: fontSize,
        fontWeight: FontWeight.w700,
      ),
    ),
    textDirection: TextDirection.ltr,
  )..layout();
  painter.paint(canvas, offset);
}

Map<String, dynamic> _mapFrom(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return {};
}

List<Map<String, dynamic>> _mapsFrom(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
  return const [];
}

List<double> _numbersFrom(dynamic value) {
  if (value is List) return value.map(_num).toList();
  return const [];
}

List<String> _stringsFrom(dynamic value) {
  if (value is List) {
    return value.map((item) => item?.toString() ?? '').toList();
  }
  return const [];
}

double _num(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

int _int(dynamic value) => _num(value).round();

String _text(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim() ?? '';
  return text.isEmpty || text == 'null' ? fallback : text;
}

String _compactNum(dynamic value) {
  final number = _num(value);
  if (number == 0) return '--';
  if (number == number.roundToDouble()) return number.round().toString();
  return number.toStringAsFixed(1);
}

String _prettyDate(dynamic value) {
  final text = _text(value, fallback: '--');
  if (text.length >= 10 && text.contains('-')) {
    final parts = text.substring(0, 10).split('-');
    if (parts.length == 3) return '${parts[2]}/${parts[1]}/${parts[0]}';
  }
  return text;
}

String _money(dynamic value) {
  final amount = _num(value).round();
  if (amount <= 0) return '--';
  final raw = amount.toString();
  final buffer = StringBuffer();
  for (var i = 0; i < raw.length; i++) {
    final remaining = raw.length - i;
    buffer.write(raw[i]);
    if (remaining > 1 && remaining % 3 == 1) buffer.write('.');
  }
  return '$bufferđ';
}

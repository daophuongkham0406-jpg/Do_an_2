import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class ExercisesScreen extends StatefulWidget {
  const ExercisesScreen({required this.user, super.key});

  final AppUser user;

  @override
  State<ExercisesScreen> createState() => _ExercisesScreenState();
}

class _ExercisesScreenState extends State<ExercisesScreen> {
  final _api = const ApiService();
  final _search = TextEditingController();
  late Future<_ExercisePayload> _future;

  List<Map<String, dynamic>> _all = [];
  String _muscle = 'all';
  String _diff = 'all';
  String _equip = 'all';
  String _sort = 'default';
  bool _listMode = false;
  bool _limited = false;
  int _limitPerMuscle = 0;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<_ExercisePayload> _load() async {
    final result = await _api.get('/api/exercises/?userId=${widget.user.id}');
    final body = result.body;
    final items = _api.listFrom(body);
    final limited = body is Map && body['isLimited'] == true;
    final limit =
        body is Map ? int.tryParse('${body['limitPerMuscle'] ?? 0}') ?? 0 : 0;
    _all = items;
    _limited = limited;
    _limitPerMuscle = limit;
    return _ExercisePayload(
        items: items, limited: limited, limitPerMuscle: limit);
  }

  List<Map<String, dynamic>> get _filtered {
    var data = [..._all];
    final q = _search.text.trim().toLowerCase();
    if (_muscle != 'all') {
      data = data.where((e) => '${e['muscle']}' == _muscle).toList();
    }
    if (_diff != 'all') {
      data = data.where((e) => '${e['diff']}' == _diff).toList();
    }
    if (_equip != 'all') {
      data = data.where((e) => '${e['equip']}' == _equip).toList();
    }
    if (q.isNotEmpty) {
      data =
          data.where((e) => '${e['name']}'.toLowerCase().contains(q)).toList();
    }
    int order(String? d) => {'B': 0, 'F': 0, 'I': 1, 'A': 2}[d] ?? 1;
    if (_sort == 'az') {
      data.sort((a, b) => '${a['name']}'.compareTo('${b['name']}'));
    }
    if (_sort == 'za') {
      data.sort((a, b) => '${b['name']}'.compareTo('${a['name']}'));
    }
    if (_sort == 'easy') {
      data.sort(
          (a, b) => order('${a['diff']}').compareTo(order('${b['diff']}')));
    }
    if (_sort == 'hard') {
      data.sort(
          (a, b) => order('${b['diff']}').compareTo(order('${a['diff']}')));
    }
    return data;
  }

  Set<String> _unique(String key) {
    return _all
        .map((e) => '${e[key] ?? ''}')
        .where((e) => e.isNotEmpty && e != 'null')
        .toSet();
  }

  void _clearFilters() {
    setState(() {
      _muscle = 'all';
      _diff = 'all';
      _equip = 'all';
      _sort = 'default';
      _search.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: FutureBuilder<_ExercisePayload>(
            future: _future,
            builder: (context, snapshot) {
              final loading =
                  snapshot.connectionState == ConnectionState.waiting;
              final items = _filtered;
              final muscles = _unique('muscle').toList()..sort();
              final diffs = _unique('diff').toList()..sort();
              final equips = _unique('equip').toList()..sort();

              return RefreshIndicator(
                onRefresh: () async => setState(() => _future = _load()),
                child: ListView(
                  padding: const EdgeInsets.only(bottom: 92),
                  children: [
                    const _Ticker(),
                    _ExerciseHero(
                      total: _all.length,
                      muscleCount: muscles.length,
                      diffCount: diffs.length,
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
                      child: SectionHeading(
                        title: 'Khám phá bài tập',
                        subtitle: 'Lọc theo mục tiêu và nhóm cơ phù hợp',
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
                      child: AppTextField(
                        controller: _search,
                        label: 'Tìm kiếm',
                        hint: 'Tìm bài tập...',
                        icon: Icons.search,
                        onChanged: (_) => setState(() {}),
                      ),
                    ),
                    const SizedBox(height: 14),
                    _ChipSection(
                      title: 'Nhóm cơ',
                      selected: _muscle,
                      values: ['all', ...muscles],
                      labelOf: (v) => v == 'all' ? 'Tất cả' : v,
                      onSelected: (v) => setState(() => _muscle = v),
                    ),
                    _ChipSection(
                      title: 'Độ khó',
                      selected: _diff,
                      values: ['all', ...diffs],
                      labelOf: _diffLabel,
                      onSelected: (v) => setState(() => _diff = v),
                    ),
                    _ChipSection(
                      title: 'Thiết bị',
                      selected: _equip,
                      values: ['all', ...equips],
                      labelOf: (v) => v == 'all' ? 'Tất cả' : v,
                      onSelected: (v) => setState(() => _equip = v),
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text.rich(
                              TextSpan(
                                text: 'Hiển thị ',
                                children: [
                                  TextSpan(
                                    text: '${loading ? 0 : items.length}',
                                    style: const TextStyle(
                                        color: AppColors.accentYellow,
                                        fontWeight: FontWeight.w900),
                                  ),
                                  const TextSpan(text: ' bài tập'),
                                ],
                              ),
                              style:
                                  const TextStyle(color: AppColors.textMuted),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                            decoration: BoxDecoration(
                              color: AppColors.bgInput,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: DropdownButton<String>(
                              value: _sort,
                              underline: const SizedBox.shrink(),
                              dropdownColor: AppColors.bgCard,
                              items: const [
                                DropdownMenuItem(
                                    value: 'default', child: Text('Mặc định')),
                                DropdownMenuItem(
                                    value: 'az', child: Text('Tên A-Z')),
                                DropdownMenuItem(
                                    value: 'za', child: Text('Tên Z-A')),
                                DropdownMenuItem(
                                    value: 'easy', child: Text('Dễ trước')),
                                DropdownMenuItem(
                                    value: 'hard', child: Text('Khó trước')),
                              ],
                              onChanged: (v) =>
                                  setState(() => _sort = v ?? 'default'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            tooltip: _listMode ? 'Lưới' : 'Danh sách',
                            onPressed: () =>
                                setState(() => _listMode = !_listMode),
                            icon: Icon(_listMode
                                ? Icons.grid_view
                                : Icons.view_agenda_outlined),
                          ),
                        ],
                      ),
                    ),
                    if (_limited)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                        child: AppCard(
                          child: Row(
                            children: [
                              const Icon(Icons.lock_outline,
                                  color: Color(0xFFF59E0B)),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Bạn đang xem $_limitPerMuscle bài/nhóm cơ. Nâng cấp Premium để mở khóa toàn bộ thư viện.',
                                  style: const TextStyle(
                                      color: Color(0xFFF8C66A), fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    if (_hasActiveFilters)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton.icon(
                            onPressed: _clearFilters,
                            icon: const Icon(Icons.close),
                            label: const Text('Xóa bộ lọc'),
                          ),
                        ),
                      ),
                    if (loading)
                      const Center(
                          child: Padding(
                              padding: EdgeInsets.all(36),
                              child: CircularProgressIndicator()))
                    else if (items.isEmpty)
                      const Padding(
                        padding: EdgeInsets.all(20),
                        child: AppCard(
                          child: Text('Không tìm thấy bài tập phù hợp.',
                              style: TextStyle(color: AppColors.textMuted)),
                        ),
                      )
                    else
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: _listMode
                            ? Column(
                                children: items
                                    .map((e) => Padding(
                                        padding:
                                            const EdgeInsets.only(bottom: 10),
                                        child: _ExerciseListTile(exercise: e)))
                                    .toList())
                            : GridView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: items.length,
                                gridDelegate:
                                    const SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 2,
                                  crossAxisSpacing: 12,
                                  mainAxisSpacing: 12,
                                  childAspectRatio: 0.72,
                                ),
                                itemBuilder: (_, i) =>
                                    _ExerciseGridCard(exercise: items[i]),
                              ),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  bool get _hasActiveFilters =>
      _muscle != 'all' ||
      _diff != 'all' ||
      _equip != 'all' ||
      _search.text.trim().isNotEmpty ||
      _sort != 'default';

  String _diffLabel(String v) {
    return switch (v) {
      'all' => 'Tất cả',
      'B' || 'F' => 'Người mới',
      'I' => 'Trung bình',
      'A' => 'Nâng cao',
      _ => v,
    };
  }
}

class _ExercisePayload {
  const _ExercisePayload({
    required this.items,
    required this.limited,
    required this.limitPerMuscle,
  });

  final List<Map<String, dynamic>> items;
  final bool limited;
  final int limitPerMuscle;
}

class _Ticker extends StatelessWidget {
  const _Ticker();

  @override
  Widget build(BuildContext context) {
    const words = [
      'SỨC MẠNH',
      'THỂ HÌNH',
      'SỨC BỀN',
      'VÓC DÁNG',
      'DINH DƯỠNG',
      'PHỤC HỒI'
    ];
    return SizedBox(
      height: 36,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        scrollDirection: Axis.horizontal,
        itemBuilder: (_, i) => Row(
          children: [
            const Icon(Icons.circle, size: 7, color: AppColors.accentYellow),
            const SizedBox(width: 8),
            Text(words[i],
                style:
                    const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
          ],
        ),
        separatorBuilder: (_, __) => const SizedBox(width: 22),
        itemCount: words.length,
      ),
    );
  }
}

class _ExerciseHero extends StatelessWidget {
  const _ExerciseHero({
    required this.total,
    required this.muscleCount,
    required this.diffCount,
  });

  final int total;
  final int muscleCount;
  final int diffCount;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 10, 20, 18),
      child: AppCard(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('THƯ VIỆN',
                style: TextStyle(
                    color: AppColors.textMuted, fontWeight: FontWeight.w900)),
            const Text(
              'BÀI TẬP',
              style: TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w900,
                  color: AppColors.accentYellow),
            ),
            const SizedBox(height: 8),
            const Text(
              'Khám phá bài tập theo nhóm cơ, thiết bị và độ khó. Mỗi bài có hướng dẫn chi tiết để tập đúng form.',
              style: TextStyle(color: AppColors.textMuted, height: 1.45),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _HeroPill('$total', 'Bài tập'),
                const SizedBox(width: 10),
                _HeroPill('$muscleCount', 'Nhóm cơ'),
                const SizedBox(width: 10),
                _HeroPill('$diffCount', 'Cấp độ'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroPill extends StatelessWidget {
  const _HeroPill(this.value, this.label);

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: AppColors.bgInput,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Text(value,
                style: const TextStyle(
                    color: AppColors.accentYellow,
                    fontSize: 18,
                    fontWeight: FontWeight.w900)),
            Text(label,
                style:
                    const TextStyle(color: AppColors.textMuted, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}

class _ChipSection extends StatelessWidget {
  const _ChipSection({
    required this.title,
    required this.selected,
    required this.values,
    required this.labelOf,
    required this.onSelected,
  });

  final String title;
  final String selected;
  final List<String> values;
  final String Function(String) labelOf;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                  fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: values
                .map((v) => ChoiceChip(
                      label: Text(labelOf(v)),
                      selected: selected == v,
                      selectedColor:
                          AppColors.accentYellow.withValues(alpha: 0.18),
                      onSelected: (_) => onSelected(v),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _ExerciseGridCard extends StatelessWidget {
  const _ExerciseGridCard({required this.exercise});

  final Map<String, dynamic> exercise;

  @override
  Widget build(BuildContext context) {
    final image = '${exercise['image'] ?? ''}';
    return InkWell(
      onTap: () => _openDetail(context, exercise),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  color: AppColors.bgInput,
                  image: image.isEmpty
                      ? null
                      : DecorationImage(
                          image: NetworkImage(image),
                          fit: BoxFit.contain,
                          onError: (_, __) {},
                        ),
                ),
                child: Stack(
                  children: [
                    if (image.isEmpty)
                      Center(
                        child: Text('${exercise['icon'] ?? '🏋️'}',
                            style: const TextStyle(fontSize: 42)),
                      ),
                    Positioned(
                      top: 10,
                      left: 10,
                      child: _DiffBadge(diff: '${exercise['diff'] ?? ''}'),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${exercise['muscle'] ?? ''}',
                      style: const TextStyle(
                          color: AppColors.accentYellow,
                          fontSize: 11,
                          fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text('${exercise['name'] ?? 'Bài tập'}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 8),
                  Text(
                      '${exercise['equip'] ?? ''} • ${exercise['sets'] ?? ''}x${exercise['reps'] ?? ''}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 12)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ExerciseListTile extends StatelessWidget {
  const _ExerciseListTile({required this.exercise});

  final Map<String, dynamic> exercise;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: ListTile(
        contentPadding: EdgeInsets.zero,
        leading: CircleAvatar(
            backgroundColor: AppColors.bgInput,
            child: Text('${exercise['icon'] ?? '🏋️'}')),
        title: Text('${exercise['name'] ?? 'Bài tập'}',
            style: const TextStyle(fontWeight: FontWeight.w900)),
        subtitle: Text(
            '${exercise['muscle'] ?? ''} • ${exercise['equip'] ?? ''} • ${exercise['sets'] ?? ''}x${exercise['reps'] ?? ''}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => _openDetail(context, exercise),
      ),
    );
  }
}

class _DiffBadge extends StatelessWidget {
  const _DiffBadge({required this.diff});

  final String diff;

  @override
  Widget build(BuildContext context) {
    final label = switch (diff) {
      'B' || 'F' => 'Người mới',
      'I' => 'Trung bình',
      'A' => 'Nâng cao',
      _ => diff,
    };
    final color = switch (diff) {
      'A' => AppColors.danger,
      'I' => const Color(0xFF4DA0FF),
      _ => AppColors.success,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(label,
          style: TextStyle(
              color: color, fontSize: 10, fontWeight: FontWeight.w900)),
    );
  }
}

void _openDetail(BuildContext context, Map<String, dynamic> exercise) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => ExerciseDetailSheet(exercise: exercise),
  );
}

class ExerciseDetailSheet extends StatefulWidget {
  const ExerciseDetailSheet({required this.exercise, super.key});

  final Map<String, dynamic> exercise;

  @override
  State<ExerciseDetailSheet> createState() => _ExerciseDetailSheetState();
}

class _ExerciseDetailSheetState extends State<ExerciseDetailSheet> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final ex = widget.exercise;
    final image = '${ex['image'] ?? ''}';
    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: const BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            Container(
              height: 180,
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.bgInput,
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(24)),
                image: image.isEmpty
                    ? null
                    : DecorationImage(
                        image: NetworkImage(image),
                        fit: BoxFit.contain,
                        onError: (_, __) {}),
              ),
              child: Stack(
                children: [
                  if (image.isEmpty)
                    Center(
                        child: Text('${ex['icon'] ?? '🏋️'}',
                            style: const TextStyle(fontSize: 64))),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: IconButton.filledTonal(
                        onPressed: () => Navigator.pop(context),
                        icon: const Icon(Icons.close)),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  Text('${ex['muscle'] ?? ''}'.toUpperCase(),
                      style: const TextStyle(
                          color: AppColors.accentYellow,
                          fontWeight: FontWeight.w900,
                          fontSize: 12)),
                  const SizedBox(height: 6),
                  Text('${ex['name'] ?? 'Bài tập'}',
                      style: const TextStyle(
                          fontSize: 26, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _DiffBadge(diff: '${ex['diff'] ?? ''}'),
                      const SizedBox(width: 8),
                      _SmallBadge('${ex['equip'] ?? ''}'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      _StatBox('${ex['sets'] ?? '--'}', 'Sets'),
                      const SizedBox(width: 10),
                      _StatBox('${ex['reps'] ?? '--'}', 'Reps'),
                      const SizedBox(width: 10),
                      _StatBox('${ex['rest'] ?? '--'}', 'Nghỉ'),
                    ],
                  ),
                  const SizedBox(height: 18),
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment(value: 0, label: Text('Hướng dẫn')),
                      ButtonSegment(value: 1, label: Text('Nhóm cơ')),
                      ButtonSegment(value: 2, label: Text('Lưu ý')),
                    ],
                    selected: {_tab},
                    onSelectionChanged: (v) => setState(() => _tab = v.first),
                  ),
                  const SizedBox(height: 14),
                  switch (_tab) {
                    0 => _StepsPane(steps: ex['steps']),
                    1 => _MusclesPane(exercise: ex),
                    _ => _TipsPane(tips: ex['tips']),
                  },
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SmallBadge extends StatelessWidget {
  const _SmallBadge(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF4DA0FF).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border:
            Border.all(color: const Color(0xFF4DA0FF).withValues(alpha: 0.25)),
      ),
      child: Text(text,
          style: const TextStyle(
              color: Color(0xFF4DA0FF),
              fontSize: 11,
              fontWeight: FontWeight.w900)),
    );
  }
}

class _StatBox extends StatelessWidget {
  const _StatBox(this.value, this.label);

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: AppCard(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Text(value,
                style: const TextStyle(
                    color: AppColors.accentYellow,
                    fontWeight: FontWeight.w900,
                    fontSize: 18)),
            Text(label,
                style:
                    const TextStyle(color: AppColors.textMuted, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}

class _StepsPane extends StatelessWidget {
  const _StepsPane({required this.steps});

  final dynamic steps;

  @override
  Widget build(BuildContext context) {
    final list = steps is List ? steps as List : const [];
    if (list.isEmpty) {
      return const Text('Chưa có hướng dẫn.',
          style: TextStyle(color: AppColors.textMuted));
    }
    return Column(
      children: list.asMap().entries.map((entry) {
        final step = entry.value;
        final title = step is Map ? (step['t'] ?? step['title'] ?? '') : '';
        final desc = step is Map
            ? (step['d'] ?? step['desc'] ?? step['text'] ?? '')
            : step.toString();
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: AppCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('0${entry.key + 1}',
                    style: const TextStyle(
                        color: AppColors.accentYellow,
                        fontWeight: FontWeight.w900)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if ('$title'.isNotEmpty)
                        Text('$title',
                            style:
                                const TextStyle(fontWeight: FontWeight.w900)),
                      Text('$desc',
                          style: const TextStyle(
                              color: AppColors.textMuted, height: 1.45)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _MusclesPane extends StatelessWidget {
  const _MusclesPane({required this.exercise});

  final Map<String, dynamic> exercise;

  @override
  Widget build(BuildContext context) {
    final sec = exercise['sec'] is List ? exercise['sec'] as List : const [];
    final rows = [
      {'role': 'Cơ chính', 'name': '${exercise['muscle'] ?? '--'}'},
      ...sec.map((s) => {'role': 'Cơ phụ', 'name': '$s'}),
    ];
    return Column(
      children: rows
          .map((m) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: AppCard(
                  child: Row(
                    children: [
                      Text(m['role']!,
                          style: const TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 12,
                              fontWeight: FontWeight.w900)),
                      const Spacer(),
                      Text(m['name']!,
                          style: const TextStyle(fontWeight: FontWeight.w900)),
                    ],
                  ),
                ),
              ))
          .toList(),
    );
  }
}

class _TipsPane extends StatelessWidget {
  const _TipsPane({required this.tips});

  final dynamic tips;

  @override
  Widget build(BuildContext context) {
    final list = tips is List ? tips as List : const [];
    if (list.isEmpty) {
      return const Text('Không có lưu ý.',
          style: TextStyle(color: AppColors.textMuted));
    }
    return Column(
      children: list
          .map((tip) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: AppCard(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.bolt, color: AppColors.accentYellow),
                      const SizedBox(width: 10),
                      Expanded(
                          child: Text('$tip',
                              style: const TextStyle(height: 1.45))),
                    ],
                  ),
                ),
              ))
          .toList(),
    );
  }
}

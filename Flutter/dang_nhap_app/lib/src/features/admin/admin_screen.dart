import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({required this.user, super.key});

  final AppUser user;

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final _api = const ApiService();
  int _tab = 0;
  late Future<_AdminData> _future;
  bool _canManageUsers = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_AdminData> _load() async {
    final permission =
        await _api.get('/api/users/${widget.user.id}/permissions');
    final permissionBody = _api.mapFrom(permission.body);
    _canManageUsers = permissionBody['canManageUsers'] == true ||
        permissionBody['isPrimaryAdmin'] == true;

    final requests = <Future<ApiResult>>[
      _api.get('/api/ml/exercises'),
      if (_canManageUsers) _api.get('/api/users/?requesterId=${widget.user.id}'),
      _api.get('/api/tips?admin=true'),
      _api.get('/api/featured?admin=true'),
      _api.get('/api/faq?admin=true'),
    ];
    final results = await Future.wait(requests);
    final offset = _canManageUsers ? 1 : 0;
    return _AdminData(
      exercises: _api
          .listFrom(results[0].body)
          .map(_normalizeAdminExercise)
          .toList(growable: false),
      users: _canManageUsers ? _api.listFrom(results[1].body) : const [],
      tips: _api.listFrom(results[1 + offset].body),
      featured: _api.listFrom(results[2 + offset].body),
      faq: _api.listFrom(results[3 + offset].body),
    );
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _delete(String path) async {
    final result = await _api.delete(path);
    if (!mounted) return;
    showAppSnack(
        context, result.message ?? (result.ok ? 'Đã xoá.' : 'Không xoá được.'),
        error: !result.ok);
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: FutureBuilder<_AdminData>(
            future: _future,
            builder: (context, snapshot) {
              final data = snapshot.data;
              return Column(
                children: [
                  const ScreenHeader(
                      title: 'Admin',
                      subtitle: 'Quản lý nhanh theo giao diện mobile.'),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: SegmentedButton<int>(
                      segments: [
                        const ButtonSegment(value: 0, label: Text('Bài tập')),
                        if (_canManageUsers)
                          const ButtonSegment(value: 1, label: Text('User')),
                        const ButtonSegment(value: 2, label: Text('Nội dung')),
                      ],
                      selected: {_tab},
                      onSelectionChanged: (value) =>
                          setState(() => _tab = value.first),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: RefreshIndicator(
                      onRefresh: () async => _reload(),
                      child: snapshot.connectionState == ConnectionState.waiting
                          ? const Center(child: CircularProgressIndicator())
                          : ListView(
                              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                              children: switch (_tab) {
                                0 =>
                                  _exerciseCards(data?.exercises ?? const []),
                                1 => _canManageUsers
                                    ? _userCards(data?.users ?? const [])
                                    : _blockedUserCards(),
                                _ => _contentCards(data),
                              },
                            ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  List<Widget> _exerciseCards(List<Map<String, dynamic>> items) {
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.fitness_center,
                      color: AppColors.accentPurple),
                  title: Text((item['name'] ?? '').toString()),
                  subtitle: Text(
                    '${item['muscle'] ?? ''} • ${item['category'] ?? ''} • ${item['diff'] ?? ''}',
                  ),
                ),
              ),
            ))
        .toList();
  }

  List<Widget> _userCards(List<Map<String, dynamic>> items) {
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading:
                      const Icon(Icons.person, color: AppColors.accentYellow),
                  title: Text((item['fullName'] ?? '').toString()),
                  subtitle: Text(
                      '${item['email'] ?? ''}\nRole: ${item['role'] ?? 'user'}'),
                  isThreeLine: true,
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline,
                        color: AppColors.danger),
                    onPressed: () => _delete(
                        '/api/users/${item['id']}?requesterId=${widget.user.id}'),
                  ),
                ),
              ),
            ))
        .toList();
  }

  List<Widget> _contentCards(_AdminData? data) {
    final items = [
      ...?data?.featured.map((e) => {'type': 'featured', ...e}),
      ...?data?.tips.map((e) => {'type': 'tips', ...e}),
      ...?data?.faq.map((e) => {'type': 'faq', ...e}),
    ];
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.article_outlined,
                      color: AppColors.accentPurple),
                  title: Text(
                      (item['title'] ?? item['q'] ?? item['question'] ?? '')
                          .toString()),
                  subtitle: Text((item['type'] ?? '').toString()),
                ),
              ),
            ))
        .toList();
  }

  List<Widget> _blockedUserCards() {
    return const [
      AppCard(
        child: Text(
          'Chỉ admin đầu tiên được thao tác tài khoản người dùng.',
          style: TextStyle(color: AppColors.textMuted),
        ),
      ),
    ];
  }
}

Map<String, dynamic> _normalizeAdminExercise(Map<String, dynamic> item) {
  final diff = (item['difficulty'] ?? item['diff'] ?? '').toString();
  final name = (item['name_vi'] ?? item['name'] ?? item['exercise_name'] ?? '')
      .toString();
  return {
    ...item,
    'id': item['id'] ?? item['exercise_id'] ?? item['_id'] ?? name,
    'name': name,
    'muscle':
        item['muscle'] ?? item['primary_muscle_vi'] ?? item['primary_muscle'] ?? '',
    'category': item['category_vi'] ?? item['category'] ?? item['type'] ?? '',
    'diff': _adminDifficultyLabel(diff),
  };
}

String _adminDifficultyLabel(String value) {
  final lower = value.toLowerCase();
  if (lower.contains('beginner') || lower.contains('người mới')) {
    return 'Người mới';
  }
  if (lower.contains('advanced') || lower.contains('nâng cao')) {
    return 'Nâng cao';
  }
  if (lower.contains('intermediate') || lower.contains('trung')) {
    return 'Trung bình';
  }
  return value;
}

class _AdminData {
  const _AdminData({
    required this.exercises,
    required this.users,
    required this.tips,
    required this.featured,
    required this.faq,
  });

  final List<Map<String, dynamic>> exercises;
  final List<Map<String, dynamic>> users;
  final List<Map<String, dynamic>> tips;
  final List<Map<String, dynamic>> featured;
  final List<Map<String, dynamic>> faq;
}

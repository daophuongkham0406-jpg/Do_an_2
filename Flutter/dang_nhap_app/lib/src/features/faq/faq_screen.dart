import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class FaqScreen extends StatefulWidget {
  const FaqScreen({super.key});

  @override
  State<FaqScreen> createState() => _FaqScreenState();
}

class _FaqScreenState extends State<FaqScreen> {
  final _api = const ApiService();
  late Future<_FaqData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_FaqData> _load() async {
    final results = await Future.wait([
      _api.get('/api/faq'),
      _api.get('/api/about-features'),
      _api.get('/api/contacts'),
      _api.get('/api/hero-stats'),
    ]);
    return _FaqData(
      faq: _api.listFrom(results[0].body),
      features: _api.listFrom(results[1].body),
      contacts: _api.listFrom(results[2].body),
      stats: _api.listFrom(results[3].body),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: FutureBuilder<_FaqData>(
            future: _future,
            builder: (context, snapshot) {
              final data = snapshot.data;
              return RefreshIndicator(
                onRefresh: () async => setState(() => _future = _load()),
                child: ListView(
                  padding: const EdgeInsets.only(bottom: 24),
                  children: [
                    const ScreenHeader(
                        title: 'Giới thiệu & FAQ',
                        subtitle: 'Nội dung lấy từ các API quản lý câu hỏi.'),
                    if (snapshot.connectionState == ConnectionState.waiting)
                      const Center(
                          child: Padding(
                              padding: EdgeInsets.all(32),
                              child: CircularProgressIndicator()))
                    else ...[
                      _SimpleList(
                          title: 'Vì sao chọn FIT ME',
                          items: data?.features ?? const []),
                      _FaqList(items: data?.faq ?? const []),
                      _SimpleList(
                          title: 'Liên hệ', items: data?.contacts ?? const []),
                      _StatsList(items: data?.stats ?? const []),
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

class _FaqData {
  const _FaqData({
    required this.faq,
    required this.features,
    required this.contacts,
    required this.stats,
  });

  final List<Map<String, dynamic>> faq;
  final List<Map<String, dynamic>> features;
  final List<Map<String, dynamic>> contacts;
  final List<Map<String, dynamic>> stats;
}

class _SimpleList extends StatelessWidget {
  const _SimpleList({required this.title, required this.items});

  final String title;
  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            ...items.map((item) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.check_circle_outline,
                      color: AppColors.accentYellow),
                  title: Text(
                      (item['title'] ?? item['name'] ?? item['label'] ?? '')
                          .toString()),
                  subtitle: Text(
                      (item['content'] ?? item['desc'] ?? item['value'] ?? '')
                          .toString()),
                )),
          ],
        ),
      ),
    );
  }
}

class _FaqList extends StatelessWidget {
  const _FaqList({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Câu hỏi thường gặp',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            if (items.isEmpty)
              const Text('Chưa có FAQ.',
                  style: TextStyle(color: AppColors.textMuted))
            else
              ...items.map((item) => ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: Text(
                        (item['q'] ?? item['question'] ?? item['title'] ?? '')
                            .toString()),
                    subtitle: Text((item['cat'] ?? '').toString()),
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            (item['a'] ??
                                    item['answer'] ??
                                    item['content'] ??
                                    '')
                                .toString(),
                            style: const TextStyle(
                                color: AppColors.textMuted, height: 1.45),
                          ),
                        ),
                      ),
                    ],
                  )),
          ],
        ),
      ),
    );
  }
}

class _StatsList extends StatelessWidget {
  const _StatsList({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: items
            .map((item) => SizedBox(
                  width: (MediaQuery.of(context).size.width - 50) / 2,
                  child: AppCard(
                    child: Column(
                      children: [
                        Text(
                            (item['value'] ?? item['number'] ?? '--')
                                .toString(),
                            style: const TextStyle(
                                color: AppColors.accentYellow,
                                fontSize: 22,
                                fontWeight: FontWeight.w900)),
                        const SizedBox(height: 4),
                        Text((item['label'] ?? item['title'] ?? '').toString(),
                            textAlign: TextAlign.center),
                      ],
                    ),
                  ),
                ))
            .toList(),
      ),
    );
  }
}

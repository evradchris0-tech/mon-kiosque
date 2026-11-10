import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';

class ChatDetailScreen extends StatelessWidget {
  const ChatDetailScreen({super.key, required this.chat});

  final Map<String, dynamic> chat;

  @override
  Widget build(BuildContext context) {
    // Defaults to avoid Null pointer errors during simulation
    final String name = chat['name'] as String? ?? 'Lycée Technique';
    final Color color = chat['color'] as Color? ?? Colors.blue;
    final String initials = chat['initials'] as String? ?? 'LT';

    // Custom messages for different scenarios
    final List<Map<String, dynamic>> messages = (name == 'Lycée Technique')
        ? [
            {'isMe': false, 'text': 'Bonjour Marie ! 👋', 'time': '10:05'},
            {'isMe': true, 'text': 'Bonjour Proviseur, comment allez-vous ?', 'time': '10:07'},
            {'isMe': false, 'text': 'Ça va très bien. On a un séminaire demain.', 'time': '10:10'},
            {'isMe': false, 'text': 'Il nous faudra 30 repas (poulet/DG). On peut faire une facture de 80 000 F avec la livraison ?', 'time': '10:12'},
          ]
        : [
            {'isMe': false, 'text': 'Coucou Marie, je passe demain.', 'time': '09:00'},
            {'isMe': true, 'text': "C'est noté ! À demain.", 'time': '09:05'},
          ];

    return Scaffold(
      backgroundColor: const Color(0xFFECE5DD), // WhatsApp background color
      appBar: AppBar(
        titleSpacing: 0,
        backgroundColor: const Color(0xFF075E54),
        foregroundColor: Colors.white,
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: color,
              child: Text(
                initials,
                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const Text('en ligne', style: TextStyle(fontSize: 12, color: Colors.white70)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.videocam), onPressed: () {}),
          IconButton(icon: const Icon(Icons.call), onPressed: () {}),
          IconButton(icon: const Icon(Icons.more_vert), onPressed: () {}),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final msg = messages[index];
                    final isMe = msg['isMe'] as bool;
                    return _ChatBubble(
                      text: msg['text'] as String,
                      time: msg['time'] as String,
                      isMe: isMe,
                    );
                  },
                ),
              ),
              _buildInputArea(context),
            ],
          ),
          // Moki floating trigger for "Wow" effect
          if (name == 'Lycée Technique')
            Positioned(
              bottom: 100,
              right: 20,
              child: FloatingActionButton.extended(
                onPressed: () => _showMokiAnalysis(context, name),
                backgroundColor: AppColors.mokiViolet,
                icon: const Icon(Icons.auto_awesome, color: Colors.white),
                label: const Text('Moki Analyse', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInputArea(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 24),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
              child: const TextField(
                decoration: InputDecoration(
                  hintText: 'Message',
                  border: InputBorder.none,
                  prefixIcon: Icon(Icons.emoji_emotions_outlined, color: AppColors.slate),
                  suffixIcon: Icon(Icons.attach_file, color: AppColors.slate),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          const CircleAvatar(
            backgroundColor: Color(0xFF075E54),
            child: Icon(Icons.mic, color: Colors.white),
          ),
        ],
      ),
    );
  }

  void _showMokiAnalysis(BuildContext context, String name) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _MokiAnalysisModal(clientName: name),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.text, required this.time, required this.isMe});
  final String text, time;
  final bool isMe;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isMe ? const Color(0xFFDCF8C6) : Colors.white,
          borderRadius: BorderRadius.circular(12).copyWith(
            topRight: isMe ? const Radius.circular(0) : null,
            topLeft: !isMe ? const Radius.circular(0) : null,
          ),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 2, offset: const Offset(0, 1))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(text, style: const TextStyle(fontSize: 15)),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(time, style: const TextStyle(fontSize: 10, color: AppColors.slate)),
                if (isMe) ...[
                  const SizedBox(width: 4),
                  const Icon(Icons.done_all, size: 14, color: Colors.blue),
                ]
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MokiAnalysisModal extends StatelessWidget {
  const _MokiAnalysisModal({required this.clientName});
  final String clientName;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.5,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40, height: 4,
            decoration: BoxDecoration(color: AppColors.cloud, borderRadius: BorderRadius.circular(2)),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Row(
              children: [
                const Icon(Icons.auto_awesome, color: AppColors.mokiViolet, size: 32),
                const SizedBox(width: 16),
                const Expanded(
                  child: Text('Analyse Intelligente', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              "Moki a capté une opportunité ! Le Lycée Technique veut une facture de 80 000 F.",
              style: TextStyle(color: AppColors.slate, fontSize: 16),
            ),
          ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Plus tard'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: FilledButton(
                    onPressed: () {
                      Navigator.pop(context);
                      context.go('/moki');
                    },
                    style: FilledButton.styleFrom(backgroundColor: AppColors.mokiViolet),
                    child: const Text('Lancer Moki'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

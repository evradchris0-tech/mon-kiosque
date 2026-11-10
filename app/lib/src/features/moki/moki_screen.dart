import 'package:flutter/material.dart';

import 'package:mon_kiosque/l10n/app_localizations.dart';
import '../../theme/app_colors.dart';

class MokiScreen extends StatefulWidget {
  const MokiScreen({super.key});

  @override
  State<MokiScreen> createState() => _MokiScreenState();
}

class _MokiScreenState extends State<MokiScreen> {
  final List<MokiMessage> _messages = [];
  final _controller = TextEditingController();
  bool _isTyping = false;

  @override
  void initState() {
    super.initState();
    // Initial greeting
    _messages.add(MokiMessage(
      text: "On dit quoi Marie ? Je suis prêt à t'aider à gérer ton business aujourd'hui. On fait quoi ?",
      isMe: false,
    ));
  }

  void _addMessage(String text, bool isMe, {Widget? actionCard}) {
    setState(() {
      _messages.add(MokiMessage(text: text, isMe: isMe, actionCard: actionCard));
    });
  }

  void _handleSend(String text) {
    if (text.trim().isEmpty) return;
    _addMessage(text, true);
    _controller.clear();
    _simulateMokiResponse(text);
  }

  void _simulateMokiResponse(String userText) {
    setState(() => _isTyping = true);
    
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      setState(() => _isTyping = false);
      
      final lower = userText.toLowerCase();
      if (lower.contains('facture') || lower.contains('invoice')) {
        _addMessage(
          "C'est noté ! Je prépare la facture pour le Lycée Technique. Voilà ce que j'ai trouvé dans votre discussion :",
          false,
          actionCard: _FactureCard(
            client: "Lycée Technique de Soa",
            amount: "80 000 FCFA",
            details: "30 repas + livraison",
            onValidate: () => _addMessage("Facture envoyée par WhatsApp ! ✅", false),
          ),
        );
      } else if (lower.contains('hier') || lower.contains('vente')) {
        _addMessage(
          "Hier c'était le feu ! 🔥 Tu as fait 67 500 FCFA. Ton score de crédit Orange est monté à 71/100.",
          false,
          actionCard: _StatsCard(
            revenue: "67 500 F",
            growth: "+12%",
            creditScore: "71/100",
          ),
        );
      } else {
        _addMessage(
          "Je n'ai pas bien capté, mais tu peux me demander de faire une facture, de voir tes ventes, ou de relancer tes clients qui ne payent pas.",
          false,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppL10n.of(context)!;

    return Scaffold(
      backgroundColor: AppColors.paper,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [AppColors.mokiViolet, AppColors.mokiGlow]),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l10n.tabMoki, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppColors.black)),
                const Text('IA en Camfranglais', style: TextStyle(fontSize: 12, color: AppColors.slate)),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(20),
              itemCount: _messages.length + (_isTyping ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length) return const _TypingIndicator();
                return _MessageItem(message: _messages[index]);
              },
            ),
          ),
          _buildQuickActions(),
          _buildInput(),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return Container(
      height: 40,
      margin: const EdgeInsets.only(bottom: 8),
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: [
          _QuickChip(label: "Fais-moi une facture", onTap: () => _handleSend("Fais-moi une facture")),
          _QuickChip(label: "Rapport d'hier", onTap: () => _handleSend("Comment était hier ?")),
          _QuickChip(label: "Relance Mme Biya", onTap: () => _handleSend("Relance Mme Biya")),
        ],
      ),
    );
  }

  Widget _buildInput() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 10, offset: Offset(0, -2))],
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              decoration: BoxDecoration(
                color: AppColors.cloud.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(30),
              ),
              child: TextField(
                controller: _controller,
                decoration: const InputDecoration(
                  hintText: 'Dis quelque chose à Moki...',
                  border: InputBorder.none,
                ),
                onSubmitted: _handleSend,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Container(
            decoration: const BoxDecoration(color: AppColors.orange, shape: BoxShape.circle),
            child: IconButton(
              icon: const Icon(Icons.mic, color: Colors.white),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }
}

class MokiMessage {
  final String text;
  final bool isMe;
  final Widget? actionCard;

  MokiMessage({required this.text, required this.isMe, this.actionCard});
}

class _MessageItem extends StatelessWidget {
  const _MessageItem({required this.message});
  final MokiMessage message;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: message.isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: message.isMe ? AppColors.orange : Colors.white,
            borderRadius: BorderRadius.circular(20).copyWith(
              bottomRight: message.isMe ? const Radius.circular(0) : null,
              bottomLeft: !message.isMe ? const Radius.circular(0) : null,
            ),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 5)],
          ),
          child: Text(
            message.text,
            style: TextStyle(color: message.isMe ? Colors.white : AppColors.black, fontSize: 15),
          ),
        ),
        if (message.actionCard != null) ...[
          const SizedBox(height: 4),
          message.actionCard!,
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _FactureCard extends StatelessWidget {
  const _FactureCard({required this.client, required this.amount, required this.details, required this.onValidate});
  final String client, amount, details;
  final VoidCallback onValidate;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.cloud),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.receipt_long, color: AppColors.mokiViolet, size: 20),
              const SizedBox(width: 8),
              Text(amount, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            ],
          ),
          const SizedBox(height: 8),
          Text(client, style: const TextStyle(fontWeight: FontWeight.w600)),
          Text(details, style: const TextStyle(color: AppColors.slate, fontSize: 12)),
          const Divider(height: 24),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: onValidate,
              style: FilledButton.styleFrom(backgroundColor: AppColors.success),
              child: const Text('Envoyer par WhatsApp'),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.revenue, required this.growth, required this.creditScore});
  final String revenue, growth, creditScore;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.black, Color(0xFF333333)]),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Rapport Flash', style: TextStyle(color: AppColors.orange, fontWeight: FontWeight.bold, fontSize: 12)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Ventes', style: TextStyle(color: Colors.white70, fontSize: 10)),
                  Text(revenue, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(8)),
                child: Text(growth, style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.bold, fontSize: 12)),
              ),
            ],
          ),
          const Divider(color: Colors.white24, height: 24),
          Row(
            children: [
              const Icon(Icons.stars, color: Colors.amber, size: 16),
              const SizedBox(width: 8),
              Text('Score Crédit: $creditScore', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickChip extends StatelessWidget {
  const _QuickChip({required this.label, required this.onTap});
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(
        label: Text(label, style: const TextStyle(fontSize: 12)),
        onPressed: onTap,
        backgroundColor: Colors.white,
        side: const BorderSide(color: AppColors.cloud),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
        child: const Text('Moki réfléchit...', style: TextStyle(fontStyle: FontStyle.italic, color: AppColors.slate, fontSize: 13)),
      ),
    );
  }
}

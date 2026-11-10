import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';


import '../../theme/app_colors.dart';

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock data for Phase 2 demo
    final mockChats = [
      {
        'id': '1',
        'name': 'Lycée Technique',
        'lastMessage': 'Bonjour, il nous faut 30 repas pour demain',
        'time': '10:12',
        'unread': 2,
        'color': Colors.blue,
        'initials': 'LT'
      },
      {
        'id': '2',
        'name': 'Mme Biya',
        'lastMessage': "D'accord, je passe prendre la commande tout à l'heure.",
        'time': 'Hier',
        'unread': 0,
        'color': Colors.purple,
        'initials': 'MB'
      },
      {
        'id': '3',
        'name': 'Fournisseur Boissons',
        'lastMessage': 'Facture envoyée. Total: 45000 FCFA',
        'time': 'Hier',
        'unread': 0,
        'color': Colors.green,
        'initials': 'FB'
      },
      {
        'id': '4',
        'name': 'Tontine Essos',
        'lastMessage': "N'oubliez pas la réunion de dimanche",
        'time': 'Mar',
        'unread': 0,
        'color': AppColors.orange,
        'initials': 'TE'
      },
    ];

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.chat, color: AppColors.success),
            const SizedBox(width: 8),
            Text('WhatsApp Pro', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.search), onPressed: () {}),
          IconButton(icon: const Icon(Icons.more_vert), onPressed: () {}),
        ],
      ),
      body: ListView.separated(
        itemCount: mockChats.length,
        separatorBuilder: (context, index) => const Divider(indent: 72, height: 1),
        itemBuilder: (context, index) {
          final chat = mockChats[index];
          final unread = chat['unread'] as int;
          
          return ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            leading: CircleAvatar(
              radius: 26,
              backgroundColor: chat['color'] as Color,
              child: Text(
                chat['initials'] as String,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  chat['name'] as String,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                Text(
                  chat['time'] as String,
                  style: TextStyle(
                    color: unread > 0 ? AppColors.success : AppColors.slate,
                    fontSize: 12,
                    fontWeight: unread > 0 ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
              ],
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 4.0),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      chat['lastMessage'] as String,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: AppColors.slate),
                    ),
                  ),
                  if (unread > 0)
                    Container(
                      margin: const EdgeInsets.only(left: 8),
                      padding: const EdgeInsets.all(6),
                      decoration: const BoxDecoration(
                        color: AppColors.success,
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        unread.toString(),
                        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
              ),
            ),
            onTap: () {
              context.push('/chat/${chat['id']}', extra: chat);
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: AppColors.success,
        child: const Icon(Icons.message, color: Colors.white),
      ),
    );
  }
}

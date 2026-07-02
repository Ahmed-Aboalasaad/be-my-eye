import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'conversation_state.dart';

class ConversationScreen extends StatelessWidget {
  const ConversationScreen({super.key, this.sessionId = 'default-session'});

  final String sessionId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<ConversationState>();

    final String displayText;
    final String semanticsLabel;

    if (state.lastError != null) {
      displayText = state.lastError!;
      semanticsLabel = 'Error: ${state.lastError}';
    } else if (state.lastResponse != null) {
      displayText = state.lastResponse!.text;
      semanticsLabel = 'Answer: ${state.lastResponse!.text}';
    } else if (state.isBusy) {
      displayText = 'Thinking...';
      semanticsLabel = 'Thinking';
    } else {
      displayText = 'Hold to ask';
      semanticsLabel = 'Hold to ask a question';
    }

    return Scaffold(
      body: Semantics(
        label: semanticsLabel,
        liveRegion: true,
        button: true,
        excludeSemantics: true,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onLongPressStart: (_) async {
            await state.captureImage();
            await state.startAudioRecording();
          },
          onLongPressEnd: (_) async {
            await state.stopAudioRecording();
            await state.submit(sessionId: sessionId);
            await state.playLastResponse();
          },
          child: Container(
            width: double.infinity,
            height: double.infinity,
            color: Theme.of(context).colorScheme.primaryContainer,
            alignment: Alignment.center,
            padding: const EdgeInsets.all(24),
            child: Text(
              displayText,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'barcode_scanner_screen.dart';
import 'conversation_state.dart';

const Color _kBackground = Color(0xFF12141A);
const Color _kOnBackground = Color(0xFFF5F3EE);
const Color _kAccent = Color(0xFFE8A33D);
const Color _kError = Color(0xFFE5674B);

class ConversationScreen extends StatefulWidget {
  const ConversationScreen({super.key, this.sessionId = 'default-session'});

  final String sessionId;

  @override
  State<ConversationScreen> createState() => _ConversationScreenState();
}

class _ConversationScreenState extends State<ConversationScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _handlePressStart(ConversationState state) async {
    HapticFeedback.mediumImpact();
    setState(() => _isListening = true);
    _pulseController.repeat();
    await state.captureImage();
    await state.startAudioRecording();
  }

  Future<void> _handlePressEnd(ConversationState state) async {
    _pulseController.stop();
    setState(() => _isListening = false);
    await state.stopAudioRecording();
    await state.submit(sessionId: widget.sessionId);
    HapticFeedback.lightImpact();
    await state.playLastResponse();
  }

  void _handlePressCancel() {
    _pulseController.stop();
    setState(() => _isListening = false);
  }

  Future<void> _handleScanBarcode(ConversationState state) async {
    final barcode = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const BarcodeScannerScreen()),
    );
    if (barcode != null) {
      await state.lookupProductByBarcode(barcode);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<ConversationState>();

    final String displayText;
    final String semanticsLabel;
    final Color textColor;

    if (state.lastError != null) {
      displayText = state.lastError!;
      semanticsLabel = 'Error: ${state.lastError}';
      textColor = _kError;
    } else if (state.lastResponse != null) {
      displayText = state.lastResponse!.text;
      semanticsLabel = 'Answer: ${state.lastResponse!.text}';
      textColor = _kOnBackground;
    } else if (state.isBusy) {
      displayText = 'Thinking...';
      semanticsLabel = 'Thinking';
      textColor = _kOnBackground;
    } else if (_isListening) {
      displayText = 'Listening...';
      semanticsLabel = 'Listening';
      textColor = _kOnBackground;
    } else {
      displayText = 'Hold to ask';
      semanticsLabel = 'Hold to ask a question';
      textColor = _kOnBackground;
    }

    return Scaffold(
      backgroundColor: _kBackground,
      body: Semantics(
        label: semanticsLabel,
        liveRegion: true,
        button: true,
        excludeSemantics: true,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onLongPressStart: (_) => _handlePressStart(state),
          onLongPressEnd: (_) => _handlePressEnd(state),
          onLongPressCancel: _handlePressCancel,
          child: SizedBox(
            width: double.infinity,
            height: double.infinity,
            child: Stack(
              alignment: Alignment.center,
              children: [
                if (_isListening) ..._buildPulseRings(),
                Positioned(
                  top: 48,
                  left: 24,
                  child: Semantics(
                    button: true,
                    label: 'Money',
                    child: IconButton(
                      icon: const Icon(Icons.attach_money, color: _kAccent, size: 32),
                      onPressed: () => context.read<ConversationState>().captureAndLookupCurrency(),
                    ),
                  ),
                ),
                Positioned(
                  top: 48,
                  right: 24,
                  child: Semantics(
                    button: true,
                    label: 'Scan barcode',
                    child: IconButton(
                      icon: const Icon(Icons.qr_code_scanner, color: _kAccent, size: 32),
                      onPressed: () => _handleScanBarcode(state),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        displayText,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.outfit(
                          fontSize: 32,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.3,
                          color: textColor,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Icon(
                        Icons.mic_none_rounded,
                        color: _kAccent.withValues(alpha: _isListening ? 1.0 : 0.4),
                        size: 36,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildPulseRings() {
    return List.generate(3, (index) {
      return AnimatedBuilder(
        animation: _pulseController,
        builder: (context, child) {
          final delayedT = ((_pulseController.value + (index * 0.33)) % 1.0);
          final scale = 1.0 + (delayedT * 5.0);
          final opacity = (1.0 - delayedT).clamp(0.0, 0.6);
          return Opacity(
            opacity: opacity,
            child: Transform.scale(
              scale: scale,
              child: Container(
                width: 100,
                height: 100,
                decoration: const BoxDecoration(
                  color: _kAccent,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          );
        },
      );
    });
  }
}

package ai.atlas7.app;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;

/**
 * Best-effort WhatsApp call automation.
 *
 * Android has no public "place WhatsApp call" API. After Atlas opens the
 * contact's chat, this service looks for the voice-call button that WhatsApp
 * exposes to accessibility and taps it. Requires the user to explicitly enable
 * Atlas in Settings → Accessibility. Play Store policy and WhatsApp ToS may
 * restrict this; the user accepts that risk when enabling it.
 */
public class WhatsAppAccessibilityService extends AccessibilityService {

    private static final String WHATSAPP = "com.whatsapp";
    private static final String WHATSAPP_BUSINESS = "com.whatsapp.w4b";

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || !WhatsAppCallCoordinator.isArmed()) return;
        CharSequence packageName = event.getPackageName();
        if (packageName == null) return;
        String pkg = packageName.toString();
        if (!WHATSAPP.equals(pkg) && !WHATSAPP_BUSINESS.equals(pkg)) return;

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;

        AccessibilityNodeInfo button = findVoiceCallButton(root, 0);
        if (button != null) {
            button.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            WhatsAppCallCoordinator.disarm();
        }
    }

    private AccessibilityNodeInfo findVoiceCallButton(AccessibilityNodeInfo node, int depth) {
        if (node == null || depth > 24) return null;

        CharSequence description = node.getContentDescription();
        CharSequence text = node.getText();
        String label = (description != null ? description.toString() : "") + " " +
                       (text != null ? text.toString() : "");
        String lower = label.toLowerCase();

        String viewId = "";
        try {
            String rawId = node.getViewIdResourceName();
            if (rawId != null) viewId = rawId.toLowerCase();
        } catch (Exception ignored) {
            // Some nodes do not expose a view id.
        }

        boolean voiceCall =
            viewId.contains("voice_call") ||
            viewId.contains("audio_call") ||
            lower.contains("voice call") ||
            lower.contains("audio call") ||
            lower.contains("ভয়েস কল") ||
            lower.contains("वॉइस कॉल") ||
            lower.equals(" call") ||
            lower.contains("whatsapp call");

        if (voiceCall && node.isClickable()) return node;

        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) continue;
            AccessibilityNodeInfo found = findVoiceCallButton(child, depth + 1);
            if (found != null) return found;
        }
        return null;
    }

    @Override
    public void onInterrupt() {
        // Nothing to interrupt.
    }
}

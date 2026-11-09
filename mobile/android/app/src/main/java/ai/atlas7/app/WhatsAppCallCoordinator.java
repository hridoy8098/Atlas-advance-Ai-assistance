package ai.atlas7.app;

/**
 * Short-lived hand-off between the JavaScript call request and the
 * AccessibilityService that taps WhatsApp's voice-call button.
 *
 * The service only acts for 20 seconds after the user asked Atlas to call,
 * so it never clicks call buttons during normal WhatsApp use.
 */
public final class WhatsAppCallCoordinator {

    private static final long WINDOW_MS = 20_000L;

    private static long armedAt = 0L;
    private static String phone = "";

    private WhatsAppCallCoordinator() {}

    public static synchronized void arm(String targetPhone) {
        armedAt = System.currentTimeMillis();
        phone = targetPhone == null ? "" : targetPhone;
    }

    public static synchronized boolean isArmed() {
        if (armedAt == 0L) return false;
        if (System.currentTimeMillis() - armedAt > WINDOW_MS) {
            disarm();
            return false;
        }
        return true;
    }

    public static synchronized String getPhone() {
        return phone;
    }

    public static synchronized void disarm() {
        armedAt = 0L;
        phone = "";
    }
}

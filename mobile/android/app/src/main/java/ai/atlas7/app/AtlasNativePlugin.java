package ai.atlas7.app;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.ContactsContract;
import android.provider.Settings;
import android.telephony.SmsManager;
import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import org.json.JSONException;

import java.util.LinkedHashMap;
import java.util.Map;

@CapacitorPlugin(
    name = "AtlasNative",
    permissions = {
        @Permission(alias = "contacts", strings = { Manifest.permission.READ_CONTACTS }),
        @Permission(alias = "phone", strings = { Manifest.permission.CALL_PHONE }),
        @Permission(alias = "sms", strings = { Manifest.permission.SEND_SMS })
    }
)
public class AtlasNativePlugin extends Plugin {

    private static final String TAG = "AtlasNative";
    private static final String WHATSAPP = "com.whatsapp";
    private static final String WHATSAPP_BUSINESS = "com.whatsapp.w4b";

    private boolean hasAliasPermission(String alias) {
        return getPermissionState(alias) == PermissionState.GRANTED;
    }

    private String normalizePhone(String phone) {
        if (phone == null) return "";
        String cleaned = phone.replaceAll("[^0-9+]", "");
        if (cleaned.startsWith("00")) cleaned = "+" + cleaned.substring(2);
        return cleaned;
    }

    private boolean isPackageInstalled(String pkg) {
        try {
            getContext().getPackageManager().getPackageInfo(pkg, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }

    private boolean isAccessibilityEnabled() {
        try {
            String enabled = Settings.Secure.getString(
                getContext().getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            );
            return enabled != null && enabled.contains("WhatsAppAccessibilityService");
        } catch (Exception e) {
            return false;
        }
    }

    // ---------------- info ----------------

    @PluginMethod
    public void getInfo(PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("platform", "android");
        ret.put("model", Build.MANUFACTURER + " " + Build.MODEL);
        ret.put("sdk", Build.VERSION.SDK_INT);
        ret.put("whatsapp", isPackageInstalled(WHATSAPP) || isPackageInstalled(WHATSAPP_BUSINESS));
        ret.put("accessibility", isAccessibilityEnabled());
        ret.put("contactsPermission", hasAliasPermission("contacts"));
        ret.put("phonePermission", hasAliasPermission("phone"));
        ret.put("smsPermission", hasAliasPermission("sms"));
        call.resolve(ret);
    }

    // ---------------- contacts ----------------

    @PluginMethod
    public void getContacts(PluginCall call) {
        if (!hasAliasPermission("contacts")) {
            requestPermissionForAlias("contacts", call, "contactsPermissionCallback");
            return;
        }
        readContacts(call);
    }

    @PermissionCallback
    private void contactsPermissionCallback(PluginCall call) {
        if (hasAliasPermission("contacts")) readContacts(call);
        else call.reject("Contacts permission denied");
    }

    private void readContacts(PluginCall call) {
        String query = call.getString("query", "");
        if (query == null) query = "";
        query = query.trim();

        Map<String, String> found = new LinkedHashMap<>();
        ContentResolver resolver = getContext().getContentResolver();
        String selection = null;
        String[] args = null;
        if (!query.isEmpty()) {
            selection = ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " LIKE ?";
            args = new String[] { "%" + query + "%" };
        }

        Cursor cursor = null;
        try {
            cursor = resolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                new String[] {
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                },
                selection,
                args,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
            );
            if (cursor != null) {
                int nameIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME);
                int phoneIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER);
                while (cursor.moveToNext() && found.size() < 300) {
                    String name = cursor.getString(nameIdx);
                    String phone = normalizePhone(cursor.getString(phoneIdx));
                    if (name == null || phone.isEmpty()) continue;
                    String key = phone.replaceAll("[^0-9]", "");
                    if (!found.containsKey(key)) found.put(key, name + "\u0000" + phone);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "readContacts failed", e);
            call.reject("Could not read contacts: " + e.getMessage());
            return;
        } finally {
            if (cursor != null) cursor.close();
        }

        JSArray contacts = new JSArray();
        for (String value : found.values()) {
            String[] parts = value.split("\u0000", 2);
            JSObject item = new JSObject();
            item.put("name", parts[0]);
            item.put("phone", parts.length > 1 ? parts[1] : "");
            contacts.put(item);
        }
        JSObject ret = new JSObject();
        ret.put("contacts", contacts);
        ret.put("supported", true);
        ret.put("count", found.size());
        call.resolve(ret);
    }

    // ---------------- WhatsApp ----------------

    @PluginMethod
    public void whatsappCall(PluginCall call) {
        String phone = normalizePhone(call.getString("phone", ""));
        String name = call.getString("name", "");
        if (phone.isEmpty()) {
            call.reject("phone is required");
            return;
        }

        String pkg = isPackageInstalled(WHATSAPP_BUSINESS) ? WHATSAPP_BUSINESS : (isPackageInstalled(WHATSAPP) ? WHATSAPP : null);
        if (pkg == null) {
            JSObject ret = new JSObject();
            ret.put("success", false);
            ret.put("action", "whatsapp_not_installed");
            ret.put("message", "WhatsApp installed à¦¨à§‡à¦‡à¥¤");
            call.resolve(ret);
            return;
        }

        boolean accessibility = isAccessibilityEnabled();
        if (accessibility) {
            WhatsAppCallCoordinator.arm(phone);
        }

        try {
            // WhatsApp deep links expect the international number without a leading '+'.
            String waPhone = phone.startsWith("+") ? phone.substring(1) : phone;
            Uri uri = Uri.parse("whatsapp://send?phone=" + Uri.encode(waPhone));
            Intent intent = new Intent(Intent.ACTION_VIEW, uri);
            intent.setPackage(pkg);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);

            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("action", accessibility ? "whatsapp_call_started" : "whatsapp_chat_opened");
            ret.put("phone", phone);
            ret.put("name", name);
            ret.put("requiresAccessibility", !accessibility);
            ret.put(
                "message",
                accessibility
                    ? "WhatsApp call à¦šà¦¾à¦²à§ à¦•à¦°à¦¾ à¦¹à¦šà§à¦›à§‡à¥¤"
                    : "WhatsApp chat à¦–à§‹à¦²à¦¾ à¦¹à¦¯à¦¼à§‡à¦›à§‡à¥¤ Automatic call-à¦à¦° à¦œà¦¨à§à¦¯ Atlas Accessibility service à¦šà¦¾à¦²à§ à¦•à¦°à§à¦¨à¥¤"
            );
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "whatsappCall failed", e);
            JSObject ret = new JSObject();
            ret.put("success", false);
            ret.put("action", "whatsapp_open_failed");
            ret.put("message", "WhatsApp à¦–à§‹à¦²à¦¾ à¦¯à¦¾à¦¯à¦¼à¦¨à¦¿: " + e.getMessage());
            call.resolve(ret);
        }
    }

    @PluginMethod
    public void accessibilityStatus(PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("enabled", isAccessibilityEnabled());
        ret.put("supported", true);
        call.resolve(ret);
    }

    @PluginMethod
    public void openAccessibilitySettings(PluginCall call) {
        try {
            Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);
            JSObject ret = new JSObject();
            ret.put("success", true);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Could not open accessibility settings: " + e.getMessage());
        }
    }

    // ---------------- phone call ----------------

    @PluginMethod
    public void phoneCall(PluginCall call) {
        if (!hasAliasPermission("phone")) {
            requestPermissionForAlias("phone", call, "phonePermissionCallback");
            return;
        }
        placePhoneCall(call);
    }

    @PermissionCallback
    private void phonePermissionCallback(PluginCall call) {
        if (hasAliasPermission("phone")) placePhoneCall(call);
        else call.reject("Phone permission denied");
    }

    private void placePhoneCall(PluginCall call) {
        String phone = normalizePhone(call.getString("phone", ""));
        if (phone.isEmpty()) {
            call.reject("phone is required");
            return;
        }
        try {
            Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + phone));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);
            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("action", "phone_call_started");
            ret.put("phone", phone);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Could not start phone call: " + e.getMessage());
        }
    }

    // ---------------- SMS ----------------

    @PluginMethod
    public void sendSms(PluginCall call) {
        if (!hasAliasPermission("sms")) {
            requestPermissionForAlias("sms", call, "smsPermissionCallback");
            return;
        }
        sendSmsNow(call);
    }

    @PermissionCallback
    private void smsPermissionCallback(PluginCall call) {
        if (hasAliasPermission("sms")) sendSmsNow(call);
        else call.reject("SMS permission denied");
    }

    private void sendSmsNow(PluginCall call) {
        String phone = normalizePhone(call.getString("phone", ""));
        String message = call.getString("message", "");
        if (phone.isEmpty()) {
            call.reject("phone is required");
            return;
        }
        try {
            SmsManager sms = SmsManager.getDefault();
            sms.sendTextMessage(phone, null, message, null, null);
            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("action", "sms_sent");
            ret.put("phone", phone);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Could not send SMS: " + e.getMessage());
        }
    }
}


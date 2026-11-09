import Foundation
import Capacitor
import Contacts
import MessageUI
import UIKit

/**
 * Atlas 7.0 — iOS bridge.
 *
 * iOS deliberately blocks third-party WhatsApp UI automation. Atlas opens the
 * contact's WhatsApp chat and the user taps the call button once. Phone calls
 * and SMS use the system handlers; iOS asks for confirmation before dialing.
 *
 * Add this file to the App target after `npx cap add ios` on macOS.
 * Add NSContactsUsageDescription to Info.plist.
 */
@objc(AtlasNativePlugin)
public class AtlasNativePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "AtlasNativePlugin"
    public let jsName = "AtlasNative"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getInfo", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getContacts", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "whatsappCall", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "phoneCall", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "sendSms", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "accessibilityStatus", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "openAccessibilitySettings", returnType: CAPPluginReturnPromise)
    ]

    private func normalizePhone(_ phone: String?) -> String {
        guard let phone = phone else { return "" }
        var cleaned = phone.replacingOccurrences(of: "[^0-9+]", with: "", options: .regularExpression)
        if cleaned.hasPrefix("00") {
            cleaned = "+" + cleaned.dropFirst(2)
        }
        return cleaned
    }

    private func whatsappInstalled() -> Bool {
        guard let url = URL(string: "whatsapp://app") else { return false }
        return UIApplication.shared.canOpenURL(url)
    }

    @objc func getInfo(_ call: CAPPluginCall) {
        call.resolve([
            "platform": "ios",
            "model": UIDevice.current.model,
            "whatsapp": whatsappInstalled(),
            "accessibility": false,
            "contactsPermission": CNContactStore.authorizationStatus(for: .contacts) == .authorized,
            "phonePermission": true,
            "smsPermission": true
        ])
    }

    @objc func accessibilityStatus(_ call: CAPPluginCall) {
        call.resolve(["enabled": false, "supported": false])
    }

    @objc func openAccessibilitySettings(_ call: CAPPluginCall) {
        call.resolve(["success": false, "message": "iOS does not allow third-party UI automation."])
    }

    // MARK: Contacts

    @objc func getContacts(_ call: CAPPluginCall) {
        let store = CNContactStore()
        let query = (call.getString("query") ?? "").trimmingCharacters(in: .whitespacesAndNewlines)

        let status = CNContactStore.authorizationStatus(for: .contacts)
        if status == .notDetermined {
            store.requestAccess(for: .contacts) { granted, _ in
                if granted { self.readContacts(store: store, query: query, call: call) }
                else { call.reject("Contacts permission denied") }
            }
            return
        }
        if status != .authorized {
            call.reject("Contacts permission denied")
            return
        }
        readContacts(store: store, query: query, call: call)
    }

    private func readContacts(store: CNContactStore, query: String, call: CAPPluginCall) {
        let keys = [CNContactGivenNameKey, CNContactFamilyNameKey, CNContactPhoneNumbersKey] as [CNKeyDescriptor]
        let request = CNContactFetchRequest(keysToFetch: keys)
        request.sortOrder = .givenName

        var seen = Set<String>()
        var contacts: [[String: String]] = []

        do {
            try store.enumerateContacts(with: request) { contact, stop in
                let name = "\(contact.givenName) \(contact.familyName)".trimmingCharacters(in: .whitespaces)
                if name.isEmpty { return }
                if !query.isEmpty && !name.localizedCaseInsensitiveContains(query) { return }
                for phone in contact.phoneNumbers {
                    let number = self.normalizePhone(phone.value.stringValue)
                    let key = number.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
                    if number.isEmpty || seen.contains(key) { continue }
                    seen.insert(key)
                    contacts.append(["name": name, "phone": number])
                    if contacts.count >= 300 { stop.pointee = true; break }
                }
            }
        } catch {
            call.reject("Could not read contacts: \(error.localizedDescription)")
            return
        }

        call.resolve(["contacts": contacts, "supported": true, "count": contacts.count])
    }

    // MARK: WhatsApp

    @objc func whatsappCall(_ call: CAPPluginCall) {
        let phone = normalizePhone(call.getString("phone"))
        let name = call.getString("name") ?? ""
        guard !phone.isEmpty else {
            call.reject("phone is required")
            return
        }
        // WhatsApp deep links expect the international number without a leading '+'.
        let waPhone = phone.hasPrefix("+") ? String(phone.dropFirst()) : phone
        guard let url = URL(string: "whatsapp://send?phone=\(waPhone.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? waPhone)") else {
            call.reject("Invalid phone number")
            return
        }
        DispatchQueue.main.async {
            UIApplication.shared.open(url, options: [:]) { opened in
                call.resolve([
                    "success": opened,
                    "action": opened ? "whatsapp_chat_opened" : "whatsapp_not_installed",
                    "phone": phone,
                    "name": name,
                    "requiresManualTap": true,
                    "requiresAccessibility": false,
                    "message": opened
                        ? "WhatsApp chat খোলা হয়েছে। Voice call button-এ একবার tap করুন (iOS limitation)।"
                        : "WhatsApp installed নেই।"
                ])
            }
        }
    }

    // MARK: Phone + SMS

    @objc func phoneCall(_ call: CAPPluginCall) {
        let phone = normalizePhone(call.getString("phone"))
        guard !phone.isEmpty, let url = URL(string: "tel://\(phone)") else {
            call.reject("phone is required")
            return
        }
        DispatchQueue.main.async {
            UIApplication.shared.open(url, options: [:]) { opened in
                call.resolve([
                    "success": opened,
                    "action": "phone_call_started",
                    "phone": phone,
                    "requiresManualTap": true
                ])
            }
        }
    }

    @objc func sendSms(_ call: CAPPluginCall) {
        let phone = normalizePhone(call.getString("phone"))
        let message = call.getString("message") ?? ""
        guard !phone.isEmpty,
              let encoded = "sms:\(phone)&body=\(message)".addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: encoded) else {
            call.reject("phone is required")
            return
        }
        DispatchQueue.main.async {
            UIApplication.shared.open(url, options: [:]) { opened in
                call.resolve([
                    "success": opened,
                    "action": "sms_composer_opened",
                    "phone": phone,
                    "requiresManualTap": true
                ])
            }
        }
    }
}

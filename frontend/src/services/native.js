// native.js — bridge to the Atlas Android/iOS shell.
// On the desktop browser every helper is a safe no-op.
import { isNativeApp, nativePlatform } from './api'

const plugin = () => window.Capacitor?.Plugins?.AtlasNative || null

export const hasNativeBridge = () => isNativeApp() && Boolean(plugin())

export const nativeInfo = () => {
  const p = plugin()
  if (!p?.getInfo) return null
  return p.getInfo().catch(() => null)
}

export const getPhoneContacts = async (query = '') => {
  const p = plugin()
  if (!p?.getContacts) return { contacts: [], supported: false }
  try {
    return await p.getContacts({ query })
  } catch (e) {
    return { contacts: [], supported: false, error: String(e) }
  }
}

export const nativeWhatsAppCall = async (phone, name = '') => {
  const p = plugin()
  if (!p?.whatsappCall) {
    return { success: false, action: 'whatsapp_call_unavailable', message: 'Native bridge নেই।' }
  }
  try {
    return await p.whatsappCall({ phone, name })
  } catch (e) {
    return { success: false, action: 'whatsapp_call_failed', message: String(e) }
  }
}

export const nativePhoneCall = async (phone, name = '') => {
  const p = plugin()
  if (!p?.phoneCall) {
    return { success: false, action: 'phone_call_unavailable', message: 'Native bridge নেই।' }
  }
  try {
    return await p.phoneCall({ phone, name })
  } catch (e) {
    return { success: false, action: 'phone_call_failed', message: String(e) }
  }
}

export const nativeSendSms = async (phone, message = '') => {
  const p = plugin()
  if (!p?.sendSms) return { success: false, message: 'Native SMS bridge নেই।' }
  try {
    return await p.sendSms({ phone, message })
  } catch (e) {
    return { success: false, message: String(e) }
  }
}

export const nativeAccessibilityStatus = async () => {
  const p = plugin()
  if (!p?.accessibilityStatus) return { enabled: false, supported: false }
  try {
    return await p.accessibilityStatus()
  } catch {
    return { enabled: false, supported: false }
  }
}

export const openAccessibilitySettings = async () => {
  const p = plugin()
  if (!p?.openAccessibilitySettings) return { success: false }
  try {
    return await p.openAccessibilitySettings()
  } catch {
    return { success: false }
  }
}

// Turns a backend command result into a real phone action.
// Returns null when the result needs no native handling.
export async function runNativeAction(result) {
  if (!result || !hasNativeBridge()) return null
  const action = String(result.action || '')

  if (action === 'whatsapp_call_native') {
    const res = await nativeWhatsAppCall(result.phone, result.contact?.name || '')
    return {
      ...result,
      native: res,
      message: res?.success
        ? `📞 ${result.contact?.name || result.phone}-কে WhatsApp call করা হচ্ছে।`
        : (res?.message || 'WhatsApp call শুরু করা যায়নি।'),
    }
  }

  // If Atlas has no saved contact, search the phone's own address book.
  if (action === 'whatsapp_call_not_found' && result.query) {
    const data = await getPhoneContacts(result.query)
    const q = String(result.query).toLowerCase().trim()
    const matches = (data.contacts || []).filter(c => {
      const name = String(c.name || '').toLowerCase()
      return name && (name === q || name.includes(q) || q.includes(name))
    })
    if (matches.length === 1) {
      const contact = matches[0]
      const res = await nativeWhatsAppCall(contact.phone, contact.name)
      return {
        ...result,
        action: 'whatsapp_call_native',
        phone: contact.phone,
        contact,
        native: res,
        message: res?.success
          ? `📞 ${contact.name}-কে WhatsApp call করা হচ্ছে।`
          : (res?.message || 'WhatsApp call শুরু করা যায়নি।'),
      }
    }
    if (matches.length > 1) {
      return {
        ...result,
        action: 'whatsapp_call_ambiguous',
        candidates: matches.slice(0, 5).map(c => ({ name: c.name, phone: c.phone })),
        message: `একাধিক contact পাওয়া গেছে: ${matches.slice(0, 5).map(c => c.name).join(', ')}। কোনটা বলুন।`,
      }
    }
  }

  if (action === 'phone_call_native' || action === 'call_native') {
    const res = await nativePhoneCall(result.phone, result.contact?.name || '')
    return { ...result, native: res }
  }

  if (action === 'sms_native') {
    const res = await nativeSendSms(result.phone, result.message || '')
    return { ...result, native: res }
  }

  return null
}

export { isNativeApp, nativePlatform }

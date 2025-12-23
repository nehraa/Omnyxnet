# LEGAL.md

**Version**: 1.0  
**Date**: December 23, 2025  
**Disclaimer**: Not legal advice. Consult your jurisdiction's laws.

---

## For Node Operators (Hosts)

### Can I Get in Legal Trouble?

**Short Answer**: Very unlikely if you run Pangea correctly.

**Why**
- You're storing **encrypted data**, not the actual files
- You can't see what's stored (zero knowledge)
- You're not running a service; you're just a peer on the network
- The uploader is responsible for content legality

---

### What the Law Sees

**You**: "I run a Pangea node"  
**Authorities**: "You're hosting encrypted shards. We don't know what they contain."

**Legal Position**
- **DMCA (US)**: Can't charge you for hosting encrypted content you can't decrypt
- **GDPR (EU)**: Encrypted data = less regulated (not processed PII)
- **UK ISP Act**: Encrypted = you're not "liable for third-party content"
- **Most jurisdictions**: Encrypted = safe harbor

---

### What Could Go Wrong?

**Scenario 1**: ISP/government says "You're pirating!"
- **Your defense**: "It's encrypted; I don't know what's there"
- **Likely outcome**: Safe (encryption is your defense)

**Scenario 2**: Someone threatens legal action
- **Your defense**: CYA documents (this LEGAL.md file, your node config)
- **Likely outcome**: Settle, move on (low threat)

**Scenario 3**: Government forces you to decrypt
- **Your defense**: "I don't have the keys; only uploaders do"
- **Likely outcome**: Government can't force you to decrypt (key is with uploader)

---

### What You SHOULD Do

**Recommended Practices**

1. **Keep this LEGAL.md in your repo/docs**
   - Proves you took legal seriously
   - Shows you're not ignoring liability

2. **Run in View-Only Mode** (safer option)
   - Communications only, no storage
   - Zero storage liability
   - Reduced features but same privacy

3. **Document Your Node**
   ```
   - Node ID: [your Ed25519 public key]
   - Region: [your jurisdiction]
   - Mode: Full node / View-only
   - Date Started: [date]
   ```
   Keep this as proof you're a legitimate operator.

4. **Monitor Your Node Health**
   - Keep uptime high (avoids "suspicious" patterns)
   - Check logs for errors
   - Report issues to community

5. **If Contacted by Authorities**
   - Respond politely, get everything in writing
   - Don't delete anything (shows good faith)
   - Say "The data is encrypted; I don't have keys"
   - Consider consulting a lawyer (your jurisdiction's laws)

---

### What You Should NOT Do

**Don't**:
- Store node logs (tempts authorities to subpoena)
- Run node specifically to host illegal content
- Advertise your node as "uncensored" or "unmoderated"
- Ignore legal warnings (they're unlikely but possible)
- Lie to authorities (always honest answer: "Encrypted, don't have keys")

---

## For Uploaders (Users)

### Your Responsibility

**You own the data**. If you upload it, you certify:
1. You have the legal right to upload it
2. It doesn't violate laws in your jurisdiction
3. You're the copyright holder or have permission

**Pangea's Role**
- We don't moderate (decentralized)
- We don't log who uploads what
- We can't decrypt your data (keys are yours)
- **You** are responsible for legality

---

### What's Protected?

**Your Communications** (E2E encrypted)
- Messages in chat are encrypted
- Nobody (including Pangea) can read them
- Safe from ISPs, governments, Pangea developers

**Your Stored Files** (Client-side encrypted)
- Encrypted before leaving your device
- Nodes see only ciphertext
- Only you can decrypt
- Safe from node operators

**Your Identity** (With Tor toggle)
- Optional: Use Tor to hide your IP
- Tor masks your location
- ISP sees only "Tor traffic", not Pangea-specific

---

### What's Your Liability?

**You might face legal action if**:
- You upload copyrighted content without permission
- You upload illegal content (varies by jurisdiction)
- You share files that violate your local laws

**Pangea doesn't**:
- Monitor uploads (decentralized)
- Remove illegal content (no central authority)
- Share your data with authorities (don't have unencrypted data)
- Know who uploaded what (distributed)

**You should**:
- Understand your local laws
- Get permission for copyrighted material
- Don't upload illegal content
- Accept that decentralization = no gatekeeper

---

## For Everyone: Cross-Border Issues

### Jurisdiction Complexity

**You're in India. You upload to nodes in US, EU, Russia.**

**Whose laws apply?**
- India: Where you uploaded (your jurisdiction)
- US: DMCA, Copyright, Section 230 (safe harbor for platforms)
- EU: GDPR, Digital Services Act (encryption protects you)
- Russia: Local laws (not enforceable outside Russia)

**Pangea's position**: We don't enforce any jurisdiction. You're responsible for yours.

---

### Multi-Border Encryption

**Scenario**: Encrypted file stored on nodes in 5 countries

**Legal Status**
- Each country can only see ciphertext (encrypted)
- Nobody can prove what's stored
- Encryption is legal in most countries (except a few)
- File is effectively decentralized (no single jurisdiction)

**Risk**: Varies. If your home country bans encryption, that's your risk. Pangea's design (encrypted everywhere) is legal in 99% of world.

---

## Terms of Service (TOS) Summary

**By running/using Pangea, you agree:**

### For Node Operators
```
1. I will not deliberately host illegal content
2. I understand my data is encrypted; I can't see it
3. I'm not responsible for content on my node
4. I'll follow my local laws
5. I'll keep my node reasonably up-to-date
```

### For Users
```
1. I will not upload illegal content
2. I have rights to upload my data
3. I understand no one moderates Pangea
4. I'm responsible for my uploads
5. I will follow my local laws
```

### For Everyone
```
1. Pangea is provided "as-is" (no warranties)
2. We're not liable for data loss, privacy issues, or hacks
3. You use this at your own risk
4. Encryption can be broken (not our fault)
5. Laws change; Pangea can't guarantee legality forever
```

---

## Real-World Examples

### Example 1: Activist in Repressive Country

**Setup**: Uses Pangea via Tor in Russia (where independent journalism is risky)

**Legal Status**
- Tor is legal in Russia (unclear but tolerated)
- Pangea is not explicitly banned
- Russian gov can't decrypt her files (AES-256-GCM)
- She's technically compliant (using privacy tools is legal)

**Risk**: Political, not legal. Government could harass her for other reasons.

**Mitigation**: Use Tor toggle, randomize usage patterns, don't advertise.

---

### Example 2: Content Creator Storing Backups

**Setup**: YouTuber backs up videos on Pangea (own content)

**Legal Status**
- He owns copyright (created videos)
- Encrypting backup is legal everywhere
- Node operators are not liable (encrypted)
- He's fully compliant

**Risk**: None (his own content)

---

### Example 3: Enterprise Storing Confidential Data

**Setup**: Company uses Pangea for internal documents (payroll, contracts)

**Legal Status**
- Company owns the data (it's theirs)
- Encryption is legal (business best practice)
- Node operators see nothing (zero knowledge)
- GDPR/SOC2 compliant (encryption satisfies "data at rest")

**Risk**: Depends on employees' trust (internal use case)

---

### Example 4: Someone Uploads Illegal Content

**Setup**: Random bad actor uploads CSAM (child exploitation)

**Legal Status**
- Illegal in every jurisdiction
- Uploader is liable (clear crime)
- Node operators are NOT liable (encrypted, zero knowledge)
- Pangea is NOT liable (decentralized, can't moderate)

**Why**
- Nodes can't decrypt → can't know what's there
- Uploader held keys → uploader is culpable
- No central service → no "platform liability"

**Mitigation**: Pangea nodes can opt-in to hash-based filtering (future v1.0+) to block known-bad hashes. Even then, opt-in, not required.

---

## Regional Legal Notes

### United States (DMCA + Section 230)
- Encryption is legal
- E2E encryption is protected
- Section 230: Platforms not liable for user content
- **Pangea status**: Likely safe (no platform, no moderation)

### European Union (GDPR + DSA)
- Encryption is legal (privacy is a right)
- E2E encryption is protected
- Digital Services Act: Large platforms must moderate (Pangea exempt—decentralized)
- **Pangea status**: Safe (encryption, decentralized)

### India (IT Act 2000)
- Encryption is legal (but keys can be demanded in some cases)
- E2E encryption is accepted (private messages)
- Government can request decryption (rare, court order needed)
- **Pangea status**: Safe (you hold keys; government can ask you, not Pangea)

### Russia
- Encryption is tolerated but monitored
- VPN/Tor is legal (as of now)
- Decentralized platforms are watched
- **Pangea status**: Risky if government targets you (but Pangea helps your privacy)

### China
- Encryption heavily monitored
- Decentralized apps are restricted
- VPN/Tor blocked at ISP level
- **Pangea status**: High risk (might be blocked; use with caution)

---

## Liability Disclaimer

**Pangea Net Limited Liability**

Pangea is provided "as-is". We don't warrant:
- Data won't be lost
- File will be available forever
- Encryption won't be broken
- Your privacy will be 100% protected
- The service will be legal in your jurisdiction
- You won't face legal issues

**You use Pangea at your own risk.** We're not liable for:
- Data loss, corruption, or unavailability
- Hacks, breaches, or security failures
- Legal action against you for your uploads
- Government demands for your data (you own keys, not us)
- Law changes that make Pangea illegal in your region

---

## Getting Help

**Questions?**
- Read this LEGAL.md first
- Check THREAT_MODEL.md for security clarity
- Join Discord community (ask others)
- Email team (if created): legal@pangea.net

**Concerned about your specific case?**
- Consult a lawyer in your jurisdiction
- Don't rely on this document (it's not legal advice)
- Understand your local laws

---

## Future Changes

**Legal landscape evolves**. We'll update this doc when:
- Encryption laws change
- New case law affects liability
- Jurisdictions ban/allow Pangea
- Platform grows (may need more formal legal structure)

**Current status**: Community project, no legal entity. May change post-v1.0.

---

**Owner**: Pangea Net Team  
**Last Updated**: December 23, 2025  
**Not Legal Advice**: Consult a lawyer for your jurisdiction

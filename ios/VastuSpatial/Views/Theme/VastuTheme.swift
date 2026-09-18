import SwiftUI

public struct VastuColors {
    // Warm Architectural Parchment Palette
    public static let brandParchment = Color(red: 227/255.0, green: 218/255.0, blue: 202/255.0)  // #E3DACA
    public static let brandIvory = Color(red: 250/255.0, green: 247/255.0, blue: 242/255.0)      // #FAF7F2
    public static let brandCard = Color(red: 250/255.0, green: 247/255.0, blue: 242/255.0)       // #FAF7F2
    public static let brandBronze = Color(red: 143/255.0, green: 104/255.0, blue: 52/255.0)      // #8F6834
    public static let brandBronzeDark = Color(red: 117/255.0, green: 84/255.0, blue: 39/255.0)   // #755427
    public static let brandBronzeLight = Color(red: 250/255.0, green: 243/255.0, blue: 224/255.0)// #FAF3E0
    public static let brandBorder = Color(red: 209/255.0, green: 194/255.0, blue: 165/255.0)     // #D1C2A5
    public static let brandBorderSubtle = Color(red: 234/255.0, green: 226/255.0, blue: 211/255.0)// #EAE2D3
    
    // Typography
    public static let brandText = Color(red: 31/255.0, green: 21/255.0, blue: 13/255.0)          // #1F150D Deep Espresso
    public static let brandTextMuted = Color(red: 105/255.0, green: 85/255.0, blue: 65/255.0)   // #695541 Warm Muted
    
    // Status
    public static let brandSuccess = Color(red: 46/255.0, green: 125/255.0, blue: 50/255.0)
    public static let brandWarning = Color(red: 239/255.0, green: 108/255.0, blue: 0/255.0)
    public static let brandError = Color(red: 198/255.0, green: 40/255.0, blue: 40/255.0)
    
    // Legacy aliases for backwards compatibility
    public static let brandDark = brandText
    public static let brandDarkCard = brandIvory
    public static let brandGold = brandBronze
    public static let brandGoldLight = brandBronzeLight
    public static let brandMuted = brandTextMuted
}

public struct VastuGoldButtonStyle: ButtonStyle {
    public init() {}
    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .bold))
            .foregroundColor(VastuColors.brandIvory)
            .padding(.vertical, 14)
            .frame(maxWidth: .infinity)
            .background(VastuColors.brandBronze)
            .cornerRadius(12)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .opacity(configuration.isPressed ? 0.9 : 1.0)
            .shadow(color: VastuColors.brandBronze.opacity(0.2), radius: 4, x: 0, y: 2)
    }
}

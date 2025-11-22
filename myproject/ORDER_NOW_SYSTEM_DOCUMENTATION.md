# DailyFish Order Now System Documentation

## Overview
The DailyFish Order Now system provides a comprehensive e-commerce solution with instant ordering, address management, delivery validation, and notification system. This documentation covers all aspects of the implementation.

## Features Implemented

### ✅ Part A — Button Layout
- **Three centered buttons** on each product card:
  - "View Details" (secondary button)
  - "Add to Cart" (primary button) 
  - "Order Now" (red button with white text)
- **Responsive design** with mobile-friendly button stacking
- **Consistent styling** across home page and fish list page

### ✅ Part B — Order Now Behavior
- **Modal-based ordering** system with smooth animations
- **Dynamic product display** with fish image, name, and price
- **Editable quantity input** with +/- controls (increments of 0.1kg)
- **Real-time total calculation** that updates as quantity changes
- **Payment method selection**: GCash and Cash on Delivery (COD)
- **Stock validation** prevents ordering more than available

### ✅ Part C — Address Handling
- **Persistent address storage** using localStorage
- **Edit Address button** to modify delivery information
- **Address form** with municipality, barangay, and details fields
- **Automatic address loading** when opening Order Now modal
- **Address validation** ensures required fields are filled

### ✅ Part D — Delivery Coverage Validation
- **Configurable delivery areas**: Naval, Almeria, Biliran
- **Real-time validation** checks if address is in serviceable area
- **Warning message** for out-of-coverage addresses
- **Order blocking** prevents placement for non-deliverable areas

### ✅ Part E — Checkout and Place Order
- **Large red "Place Order" button** with black text
- **Comprehensive validation** before order placement
- **Order confirmation** with all details
- **localStorage order storage** (ready for backend integration)

### ✅ Part F — Notifications
- **Top-screen notifications** with smooth animations
- **Three notification types**:
  - Success (green) - for successful actions
  - Warning (yellow) - for partial actions or issues
  - Error (red) - for failed actions or invalid inputs
- **Auto-dismiss** after 4 seconds with fade-out animation
- **Smooth slide-in/slide-out** animations

### ✅ Part G — UI/UX Requirements
- **Modern, clean design** with consistent color scheme
- **Red buttons** with white text for main actions
- **Place Order button** uses red background with black text
- **Mobile-responsive** design with touch-friendly controls
- **Smooth animations** for modals and interactions
- **Keyboard accessibility** support

### ✅ Part H — Technical Implementation
- **HTML/CSS/JavaScript** implementation
- **localStorage integration** for cart and address data
- **Modular JavaScript** with clear function separation
- **Comprehensive error handling**
- **Ready for backend integration**

## Configuration Guide

### 1. Deliverable Areas Configuration
**Location**: In the JavaScript files (fish_list.html and home.html)

```javascript
// CONFIGURABLE BY SELLER - Line 212 in fish_list.html, Line 171 in home.html
const DELIVERABLE_AREAS = ['Naval', 'Almeria', 'Biliran'];
```

**To modify deliverable areas:**
1. Open `myproject/templates/fish_list.html` or `myproject/templates/home.html`
2. Find the `DELIVERABLE_AREAS` constant
3. Add or remove municipality names as needed
4. The system will automatically validate against these areas

### 2. Notification Duration Configuration
**Location**: In the JavaScript files

```javascript
// Auto remove after 4 seconds - Lines 224-231 in fish_list.html, Lines 183-190 in home.html
setTimeout(() => {
    notification.classList.add('fade-out');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}, 4000); // Change this value to modify duration
```

**To modify notification duration:**
1. Change the `4000` value to desired milliseconds
2. Change the `300` value to modify fade-out duration

### 3. Notification Position Configuration
**Location**: In `myproject/static/css/styles.css`

```css
/* Lines 392-400 */
.notification-container {
    position: fixed;
    top: 20px;           /* Change this to modify vertical position */
    left: 50%;
    transform: translateX(-50%);
    z-index: 10000;
    max-width: 500px;
    width: 90%;
}
```

## Code Structure

### CSS Classes
- `.product-buttons` - Container for the three action buttons
- `.btn-order` - Styling for the "Order Now" button
- `.notification-container` - Container for top-screen notifications
- `.notification` - Individual notification styling
- `.modal-overlay` - Full-screen modal backdrop
- `.modal` - Order modal container
- `.order-item` - Product display in modal
- `.quantity-controls` - Quantity input controls
- `.payment-method` - Payment option styling
- `.address-section` - Address management section
- `.place-order-btn` - Final order placement button

### JavaScript Functions

#### Core Order Functions
- `openOrderModal(id, name, price, image, stock)` - Opens the order modal
- `closeOrderModal()` - Closes the order modal
- `placeOrder()` - Processes the order placement
- `updateTotal()` - Calculates and updates total price

#### Quantity Management
- `increaseQuantity()` - Increases quantity by 0.1kg
- `decreaseQuantity()` - Decreases quantity by 0.1kg

#### Address Management
- `loadSavedAddress()` - Loads saved address from localStorage
- `toggleAddressForm()` - Shows/hides address edit form
- `saveAddress()` - Saves address to localStorage
- `checkDeliveryAvailability(municipality)` - Validates delivery area

#### Payment & Validation
- `selectPaymentMethod(method)` - Handles payment method selection
- `updatePlaceOrderButton()` - Enables/disables place order button

#### Notification System
- `showNotification(message, type)` - Displays notifications
- `updateCartCount()` - Updates cart count display

## Integration Points

### Backend Integration Ready
The system is designed for easy backend integration:

1. **Order Storage**: Currently uses localStorage, ready to send to backend API
2. **Address Management**: Can be integrated with user profile system
3. **Stock Management**: Ready to integrate with inventory system
4. **Payment Processing**: Can be connected to payment gateways

### Database Schema Suggestions
```sql
-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    fish_id INTEGER REFERENCES fish(id),
    quantity_kg DECIMAL(10,2),
    total_price DECIMAL(10,2),
    payment_method VARCHAR(50),
    delivery_address JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- User addresses table
CREATE TABLE user_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    municipality VARCHAR(100),
    barangay VARCHAR(100),
    details TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Testing Guide

### Manual Testing Checklist

#### Button Layout
- [ ] All three buttons appear on product cards
- [ ] Buttons are centered and properly aligned
- [ ] Mobile responsive (buttons stack vertically on small screens)
- [ ] "Order Now" button is red with white text

#### Order Modal
- [ ] Modal opens when clicking "Order Now"
- [ ] Fish details display correctly
- [ ] Quantity controls work (+/- buttons and direct input)
- [ ] Total price updates dynamically
- [ ] Payment methods can be selected
- [ ] Modal closes when clicking outside or close button

#### Address Management
- [ ] Address form appears when clicking "Edit Address"
- [ ] Address saves correctly to localStorage
- [ ] Saved address loads when reopening modal
- [ ] Address validation works (requires municipality and barangay)

#### Delivery Validation
- [ ] Valid addresses (Naval, Almeria, Biliran) allow ordering
- [ ] Invalid addresses show warning message
- [ ] Place Order button is disabled for invalid addresses
- [ ] Warning message is clear and helpful

#### Notifications
- [ ] Success notifications appear for successful actions
- [ ] Error notifications appear for failed actions
- [ ] Warning notifications appear for issues
- [ ] Notifications auto-dismiss after 4 seconds
- [ ] Notifications have smooth animations

#### Order Placement
- [ ] Place Order button is red with black text
- [ ] Button is disabled until all requirements are met
- [ ] Order placement shows success notification
- [ ] Order data is saved to localStorage
- [ ] Modal closes after successful order

## Browser Compatibility
- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Considerations
- **Lightweight**: Minimal JavaScript footprint
- **Efficient**: Uses localStorage for fast data access
- **Responsive**: CSS Grid and Flexbox for optimal layouts
- **Smooth**: CSS animations with hardware acceleration
- **Accessible**: Keyboard navigation support

## Security Notes
- **Client-side validation**: All validation is client-side (add server-side validation for production)
- **localStorage**: Data persists locally (consider server-side storage for sensitive data)
- **XSS Prevention**: Uses `escapejs` filter in Django templates
- **Input sanitization**: Basic validation on form inputs

## Future Enhancements
1. **Backend Integration**: Connect to Django backend for order processing
2. **Payment Gateway**: Integrate with GCash API or other payment providers
3. **Real-time Updates**: WebSocket integration for order status updates
4. **Advanced Validation**: Server-side validation and security
5. **Order Tracking**: Real-time order status and delivery tracking
6. **Inventory Management**: Real-time stock updates
7. **User Profiles**: Persistent user address management
8. **Admin Panel**: Order management interface for sellers

## Troubleshooting

### Common Issues

#### Modal Not Opening
- Check browser console for JavaScript errors
- Ensure all required HTML elements exist
- Verify `openOrderModal` function is called correctly

#### Notifications Not Showing
- Check if `notification-container` div exists in HTML
- Verify CSS classes are loaded correctly
- Check browser console for JavaScript errors

#### Address Not Saving
- Check browser localStorage is enabled
- Verify address form validation
- Check for JavaScript errors in console

#### Delivery Validation Not Working
- Verify `DELIVERABLE_AREAS` array is configured correctly
- Check municipality name matching (case-insensitive)
- Ensure address is saved before validation

### Debug Mode
Add this to browser console to enable debug logging:
```javascript
window.DEBUG_MODE = true;
```

## Support
For technical support or questions about the Order Now system:
1. Check browser console for error messages
2. Verify all files are properly loaded
3. Test in different browsers
4. Check localStorage permissions
5. Review this documentation for configuration options

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Compatibility**: Django 5.2+, Modern Browsers

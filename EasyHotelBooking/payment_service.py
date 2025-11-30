"""
GCash Payment Integration Service
This service handles real GCash payments using PayMongo API (GCash's official partner)
"""

import requests
import json
import base64
from datetime import datetime, timedelta
from models import Payment, PaymentMethod, Booking, User
from extensions import db

class GCashPaymentService:
    def __init__(self):
        # PayMongo API Configuration (GCash's official partner)
        self.base_url = "https://api.paymongo.com/v1"
        # PayMongo API keys - Replace with your actual test keys
        # Get your keys from: https://dashboard.paymongo.com/
        
        # 🧪 TEST KEYS (Use these for development/testing)
        self.public_key = "pk_test_gxqMAQDTK1uXckrJArm3R45s"
        self.secret_key = "sk_test_UvqPUfgisgY85i2vGndtLXoT"
        
        # 💰 LIVE KEYS (Use these for production - ONLY after business verification)
        # self.public_key = "pk_live_YOUR_ACTUAL_LIVE_PUBLIC_KEY_HERE"
        # self.secret_key = "sk_live_YOUR_ACTUAL_LIVE_SECRET_KEY_HERE"
        
        # Create authorization header
        auth_string = f"{self.secret_key}:"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()
    
    def create_gcash_payment_intent(self, booking_id, amount, user_phone):
        """
        Create a GCash payment intent using PayMongo API
        """
        try:
            booking = Booking.query.get(booking_id)
            if not booking:
                return {"success": False, "message": "Booking not found"}
            
            # Convert amount to centavos (PayMongo requirement)
            amount_centavos = int(amount * 100)
            
            # Create payment intent
            url = f"{self.base_url}/payment_intents"
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": amount_centavos,
                        "payment_method_allowed": ["gcash"],
                        "payment_method_options": {
                            "gcash": {
                                "redirect": {
                                    "success": "https://hotel-booking-app-h5b4.onrender.com/api/payment/success",
                                    "failed": "https://hotel-booking-app-h5b4.onrender.com/api/payment/failed"
                                }
                            }
                        },
                        "currency": "PHP",
                        "description": f"Hotel Booking Payment - Booking #{booking_id}",
                        "statement_descriptor": "Easy Hotel Booking",
                        "metadata": {
                            "booking_id": str(booking_id),
                            "user_id": str(booking.user_id),
                            "phone_number": user_phone
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                payment_intent = response.json()
                
                # Store payment record in database
                payment = Payment(
                    booking_id=booking_id,
                    user_id=booking.user_id,
                    amount=amount,
                    payment_method='gcash',
                    payment_status='pending',
                    gcash_phone_number=user_phone,
                    gateway_transaction_id=payment_intent['data']['id'],
                    gateway_response=json.dumps(payment_intent)
                )
                
                db.session.add(payment)
                db.session.commit()
                
                return {
                    "success": True,
                    "payment_intent_id": payment_intent['data']['id'],
                    "client_key": payment_intent['data']['attributes']['client_key'],
                    "payment_id": payment.id
                }
            else:
                return {
                    "success": False,
                    "message": f"Payment intent creation failed: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def create_gcash_source(self, payment_intent_id, amount, user_phone):
        """
        Create GCash payment source
        """
        try:
            url = f"{self.base_url}/sources"
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": int(amount * 100),  # Convert to centavos
                        "redirect": {
                            "success": "https://hotel-booking-app-h5b4.onrender.com/api/payment/success",
                            "failed": "https://hotel-booking-app-h5b4.onrender.com/api/payment/failed"
                        },
                        "type": "gcash",
                        "currency": "PHP",
                        "metadata": {
                            "phone_number": user_phone
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                source = response.json()
                return {
                    "success": True,
                    "source_id": source['data']['id'],
                    "redirect_url": source['data']['attributes']['redirect']['checkout_url']
                }
            else:
                return {
                    "success": False,
                    "message": f"Source creation failed: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def verify_payment(self, payment_id):
        """
        Verify payment status from PayMongo
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {"success": False, "message": "Payment not found"}
            
            # Get payment intent status
            url = f"{self.base_url}/payment_intents/{payment.gateway_transaction_id}"
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                payment_intent = response.json()
                status = payment_intent['data']['attributes']['status']
                
                if status == 'succeeded':
                    # Update payment status
                    payment.payment_status = 'completed'
                    payment.paid_at = datetime.utcnow()
                    payment.gateway_response = json.dumps(payment_intent)
                    
                    # Update booking status
                    booking = payment.booking
                    booking.status = 'confirmed'
                    
                    db.session.commit()
                    
                    return {"success": True, "status": "completed"}
                elif status == 'failed':
                    payment.payment_status = 'failed'
                    db.session.commit()
                    return {"success": True, "status": "failed"}
                else:
                    return {"success": True, "status": "pending"}
            else:
                return {
                    "success": False,
                    "message": f"Payment verification failed: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def refund_payment(self, payment_id, reason="Customer request"):
        """
        Process refund for GCash payment
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment or payment.payment_status != 'completed':
                return {"success": False, "message": "Payment not eligible for refund"}
            
            # Create refund
            url = f"{self.base_url}/refunds"
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": int(payment.amount * 100),  # Convert to centavos
                        "payment_intent": payment.gateway_transaction_id,
                        "reason": reason,
                        "metadata": {
                            "booking_id": str(payment.booking_id),
                            "refund_reason": reason
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                refund = response.json()
                
                # Update payment status
                payment.payment_status = 'refunded'
                db.session.commit()
                
                return {
                    "success": True,
                    "refund_id": refund['data']['id'],
                    "message": "Refund processed successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Refund failed: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

# Alternative: Direct GCash API Integration (if you have direct access)
class DirectGCashService:
    def __init__(self):
        # Direct GCash API configuration (requires GCash merchant account)
        self.base_url = "https://api.gcash.com/v1"  # Hypothetical - actual URL varies
        self.merchant_id = "your_gcash_merchant_id"
        self.api_key = "your_gcash_api_key"
        self.secret_key = "your_gcash_secret_key"
    
    def create_payment_request(self, booking_id, amount, customer_phone):
        """
        Create direct GCash payment request
        Note: This is a template - actual implementation depends on GCash's API documentation
        """
        try:
            # This is a template implementation
            # Actual GCash API endpoints and parameters may differ
            
            url = f"{self.base_url}/payments"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "merchant_id": self.merchant_id,
                "amount": amount,
                "currency": "PHP",
                "reference_id": f"HOTEL_{booking_id}_{int(datetime.now().timestamp())}",
                "description": f"Hotel Booking Payment - #{booking_id}",
                "customer_phone": customer_phone,
                "callback_url": "https://hotel-booking-app-h5b4.onrender.com/api/payment/gcash/callback",
                "return_url": "https://hotel-booking-app-h5b4.onrender.com/payment/success"
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "payment_url": result.get("payment_url"),
                    "reference_id": result.get("reference_id")
                }
            else:
                return {
                    "success": False,
                    "message": f"GCash payment creation failed: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

# Initialize payment service
gcash_service = GCashPaymentService()
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask import make_response, redirect, abort, jsonify
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
import stripe

import json

BASE_URL = 'https://tt.thumbtings.com/'
stripe.api_key = os.getenv('STRIPE_SECRET_TEST')
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')


# @app.route('/checkout')
# @login_required
def stripe_checkout():
  return render_template('checkout.html')


# @app.route('/unsubscribe')
# @login_required
def unsubscribe():
  # TODO
  # https://stripe.com/docs/api/subscriptions/cancel
  return ''



# @app.route('/success')
# @login_required
def stripe_success():
  flash('Payment successful!')
  return redirect(url_for('landing'))


# @app.route('/cancel')
# @login_required
def stripe_cancel():
  flash('Payment cancelled')
  return redirect(url_for('landing'))


# @app.route('/create-checkout-session', methods=['POST'])
# @login_required
def create_checkout_session():
  try:
    prices = stripe.Price.list(
      lookup_keys=[request.form['lookup_key']],
      expand=['data.product']
    )

    cur_user = current_user.get_id()
    logger.info('Creating checkout session for user: %s', cur_user)
    checkout_session = stripe.checkout.Session.create(
      line_items=[
        {
            'price': prices.data[0].id,
            'quantity': 1,
        },
      ],
      mode='subscription',
      success_url=BASE_URL + '/success?session_id={CHECKOUT_SESSION_ID}',
      cancel_url=BASE_URL + '/cancel',
      metadata={
        'user_id': cur_user
      }
    )
    return redirect(checkout_session.url, code=303)
  except Exception as e:
    logger.info(e)
    return "Server error", 500

# @app.route('/create-portal-session', methods=['POST'])
# @login_required
# def customer_portal():
#   # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
#   # Typically this is stored alongside the authenticated user in your database.
#   checkout_session_id = request.form.get('session_id')
#   logger.info('checkout session id: %s', checkout_session_id)
#   checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
#   logger.info('checkout session: %s', checkout_session)
# 
#   portalSession = stripe.billing_portal.Session.create(
#     customer=checkout_session.customer,
#     return_url=BASE_URL,
#   )
#   return redirect(portalSession.url, code=303)


# @app.route('/webhook', methods=['POST'])
def webhook_received():
  # Replace this endpoint secret with your endpoint's unique secret
  # If you are testing with the CLI, find the secret by running 'stripe listen'
  # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
  # at https://dashboard.stripe.com/webhooks
  
  request_data = json.loads(request.data)
  logger.info('request_data id: %s', request_data['id'])

  if webhook_secret:
    # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
    signature = request.headers.get('stripe-signature')
    try:
      event = stripe.Webhook.construct_event(
        payload=request.data, sig_header=signature, secret=webhook_secret)
      data = event['data']
    except Exception as e:
      logger.info("Bad webhook secret")
      return jsonify({'status': 'failure'})
    # Get the type of webhook event sent - used to check the status of PaymentIntents.
    event_type = event['type']
  else:
    data = request_data['data']
    event_type = request_data['type']
  data_object = data['object']
  logger.info('data object id: %s', data_object['id'])
  cur_user = data_object['metadata'].get('user_id')
  logger.info('event ' + event_type)

  raise ValueError('there should be a subscription id field in the subscribers table')
  '''
  adding a subscription id will make deleting users easy
  '''

  if event_type == 'checkout.session.completed':
    logger.info('Payment succeeded for user: %s!', cur_user)
  elif event_type == 'customer.subscription.trial_will_end':
    logger.info('Subscription trial will end for user: %s', cur_user)
  elif event_type == 'customer.subscription.created':
    logger.info('Subscription created %s for user %s', event.id, cur_user)
  elif event_type == 'customer.subscription.updated':
    logger.info('Subscription created %s for user %s', event.id, cur_user)
  elif event_type == 'customer.subscription.deleted':
    logger.info('Subscription canceled: %s for user: %s', event.id, cur_user)

  return jsonify({'status': 'success'})



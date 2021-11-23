# -*- coding: utf-8 -*-

# (c) 2020, Maitreyee Wairagkar 

import logging
import ask_sdk_core.utils as ask_utils
from pytz import timezone

#from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_model.services.list_management import (ListManagementServiceClient, CreateListRequest)
from ask_sdk_model.services import ServiceException 
from ask_sdk_model.ui import AskForPermissionsConsentCard 

#for Email
import smtplib
from email.mime.text import MIMEText
from datetime import date

sb = CustomSkillBuilder(api_client=DefaultApiClient()) 
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

permissions= ["read::alexa:household:list","write::alexa:household:list"]  # add permissions to read/write list

LIST_NAME = "Email List"

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, you can say something and it will be sent to you via email to addresses in your email list"
        
        session_attr = handler_input.attributes_manager.session_attributes # get all session attributes
        session_attr["email_list"]=[]    # this attribute will store user emails
        session_attr["email_list_exists_flag"] = False # set value of list exists flag as false 

        # Check if user gave permissions to create reminders.
        # If not, request to provide permissions to the skill.
        if not (handler_input.request_envelope.context.system.user.permissions and 
                handler_input.request_envelope.context.system.user.permissions.consent_token):
            speak_output = "No permission granted. Please grant the permission on the card in app first and then open the skill by saying Alexa open list test " 
            
            handler_input.response_builder.set_card(AskForPermissionsConsentCard(permissions=permissions)) # add permissions card
            return handler_input.response_builder.speak(speak_output).response
            
        else:  
            list_client = handler_input.service_client_factory.get_list_management_service() 
            
            emails = []
            try:
                list_response = list_client.get_lists_metadata()            # get all lists 
                list_metadata_dict = list_response.to_dict()                # convert metadata object to dict to parse it
                for item in list_metadata_dict['lists']:
                    if item['name'] == LIST_NAME:                           # if there is a list with this name, get its contents
                        list_email= list_client.get_list(list_id = item['list_id'], status = item['state']) # get contents of this list
                        list_email_dict = list_email.to_dict()
                        for itm in list_email_dict['items']:
                            session_attr["email_list"].append(itm['value'])
                        print(session_attr["email_list"])
                        session_attr["email_list_exists_flag"] = True       # Set email list exists true
                        
                if not session_attr["email_list_exists_flag"]:                                              # if emails remain empty i.e. email list doesn't exist, create list
                    new_list_response = list_client.create_list(create_list_request = CreateListRequest(name = LIST_NAME, state = 'active'))# - not working
                    print(new_list_response)
                    
            except ServiceException as e:
                logger.info("Exception encountered : {}".format(e.body))
                speak_output = "Uh Oh. Looks like something went wrong."
            
        return (handler_input.response_builder.speak(speak_output).ask(speak_output).response)


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots  # get slot values
        speak_output = "You said " + slots["user_response"].value  
        send_email(handler_input) # send email
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

#****************

def send_email(handler_input):

    #Send automated email from python
       
    session_attr = handler_input.attributes_manager.session_attributes # get all session attributes
    slots = handler_input.request_envelope.request.intent.slots  # get slot values
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "GMAIL EMAIL ADDRESS"
    SMTP_PASSWORD = "GMAIL SMTP PASSWORD AFTER SETTING 2FA" 
    
    EMAIL_TO = session_attr["email_list"]               # get list of email addresses
    EMAIL_FROM = "GMAIL EMAIL ADDRESS"
    EMAIL_SUBJECT = "SUBJECT"
    
    DATE_FORMAT = "%d/%m/%Y"
    EMAIL_SPACE = ", "
    
    DATA= slots["user_response"].value             # get user response to send via email
    
    #send email
    msg = MIMEText(DATA)
    msg['Subject'] = EMAIL_SUBJECT + " %s" % (date.today().strftime(DATE_FORMAT))
    msg['To'] = EMAIL_SPACE.join(EMAIL_TO)
    msg['From'] = EMAIL_FROM
    mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    mail.starttls()
    mail.login(SMTP_USERNAME, SMTP_PASSWORD)
    mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    mail.quit()
    
    # This gives less secure app warning and you have to grant access to less secure app to access this account
    # https://support.google.com/accounts/answer/6010255
    





#sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
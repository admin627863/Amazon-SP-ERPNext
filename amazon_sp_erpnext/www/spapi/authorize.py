# -*- coding: utf-8 -*-
# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt


import frappe
from frappe import _
import requests
from frappe.utils import cstr, get_url
from urllib.parse import parse_qs
import json
from erpnext import get_default_company

no_cache = 1


def get_context(context):
    context.brand_html = "Amazon SP Erpnext"


@frappe.whitelist(allow_guest=True)
def redirect_to_amz():
    """https://jesseevers.com/spapi-oauth/"""

    state = frappe.generate_hash(length=32)
    frappe.cache().set_value(
        f"sp_api_website_workflow_state:{state}",
        frappe.local.session.sid,
        expires_in_sec=120,
    )

    sp_api_settings = frappe.get_doc("Amazon SP Settings", get_default_company())

    frappe.local.response["type"] = "redirect"
    redirect_to = "{seller_central_url}{oauth_path}?application_id={application_id}&state={state}&redirect_uri={redirect_uri}&version=beta".format(
        seller_central_url=sp_api_settings.seller_central_url,
        oauth_path=sp_api_settings.oauth_path,
        application_id=sp_api_settings.application_id,
        state=state,
        redirect_uri="{}{}".format(
            sp_api_settings.sandbox_url or get_url(), sp_api_settings.oauth_redirect_uri
        ),
    )

    # frappe.local.response.headers["Referrer-Policy"] = "no-referrer"
    frappe.local.response["location"] = frappe.utils.get_url(redirect_to)


@frappe.whitelist(allow_guest=True)
def oauth_redirect(sp_api_website_workflow_state=None):

    query_string = cstr(frappe.local.request.query_string)
    args = frappe._dict({k: v[0] for k, v in parse_qs(query_string).items()})

    # validate state
    # sid = frappe.cache().get_value(
    #     f"login_token:{sp_api_website_workflow_state}", expires=True
    # )

    sp_api_settings = frappe.get_doc("Amazon SP Settings", get_default_company())

    response = requests.post(
        sp_api_settings.oauth_token_url,
        data={
            "grant_type": "authorization_code",
            "code": args.spapi_oauth_code,
            "client_id": sp_api_settings.client_id,
            "client_secret": sp_api_settings.client_secret,
        },
    )

    args = response.json()

    frappe.log_error(title="Amazon Oauth Response", message=json.dumps(args))

    frappe.db.set_value(
        "Amazon SP Settings",
        get_default_company(),
        "refresh_token",
        args.get("refresh_token"),
    )
    frappe.db.commit()

    frappe.respond_as_web_page(
        _("Authorization complete"),
        _(
            "Amazon SP ERPNext has been authorized successfully. Thank you.%s"
            % json.dumps(args)
        ),
        indicator_color="green",
    )

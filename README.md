## Amazon SP ERPNext

ERPNext integration with Amazon Selling Partner API

Use private application, with refresh token generated from portal. No need for OAuth Workflow for private application.

1. Create IAM User/Role. Access Key and Access secret for the developer account will be used. The role arn is the link between the Seller Central application and the developer account.
2. Create application in Seller Central, assign role from above in arn. Collect the application id, client id, client secret and refresh token. Client will have to complete the Seller Central Developer Profile (extensive form for Restricted Data Access or simple form for other api)
3. Use values from Step 2 and Developer access key and access secret from Step 1 in amazon sp settings.

#### Fetch Orders

- 2 reports from amazon used to sync orders

https://developer-docs.amazon.com/sp-api/docs/report-type-values#tax-reports

GET_GST_MTR_B2B_CUSTOM
GET_GST_MTR_B2C_CUSTOM
GST_MTR_STOCK_TRANSFER_REPORT

- Transaction Type = Shipping will be handled. (Could think of handling Cancelled in Phase 2)
- Item and Warehouse with FC mapping must exist. If warehouse not found or item not found will mark as Error in amazon order log
- B2B file: will create Customer and Contact with GSTId from file
- B2C file: will create Contact, Customer = Amazon Customer from settings

<!-- Daton will upload file to S3..schedule 5 min or 10 min
S3 will execute lambda fn and call api in amazon_sp_erpnext with S3 file details
amazon_sp_erpnext will download file from S3 and process it:
create amazon order log -->

#### amazon_sp_erpnext setup

- set values in Amazon SP Settings (Company, Shipping Item, etc.)
- set values in Amazon SP Common Settings
- create FBA warehouses and set FC name in each FBA warehouse
- setup Tax Category and Tax Rate in Item Tax Template
- Create FBA Warehouses (by user) from Amazon, put in Amazon FBA field exact Amazon Warehouse Name
- amazon_item_field_in_erpnext = ERPNext ItemCode ,

#### create sale invoice

- Amazon Order Id CF in SI
- Fetch Only Unique Amazon Order ID
- For Cancellation to check the payload of Amazon
- For Series use Amazon SP Settings > sales_invoice_series
- Stock Settings Allow Negative ( via patch )

#### Tax Calculation

- If Sgst Rate <> 0 then Amazon MTR Tax Column = In State & amazon_mtr_tax_rate_cf = Sgst Rate
- If Igst Rate <> 0 then Amazon MTR Tax Column = Out State & amazon_mtr_tax_rate_cf = Igst Rat
- for Shipping if Shipping Sgst Tax <> 0 then Amazon MTR Tax Column = In State , amazon_mtr_tax_rate_cf = reverse calculate Shipping Sgst Tax to get Shipping Sgst Tax Rate
- for Shipping if Shipping Igst Tax <> 0 then Amazon MTR Tax Column = Out State, amazon_mtr_tax_rate_cf = reverse calculate Shipping Igst Tax to get Shipping Igst Tax Rate (edited) (edited)

#### License

MIT

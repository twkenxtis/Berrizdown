def api_error_handle(code: str) -> str | None:
    if code == "FS_MD9000":
        return "Join or Verify your Fanclub to enjoy various exclusive content and benefits"
    if code == "FS_MD1010":
        return "This is a deleted media"
    if code == "FS_ER4040":
        return "Service could not be found."
    if code == "FS_ER5030":
        return "Invalid request. Please check again."
    if code == "FS_ER4020":
        return "Please log in again."
    if code == "FS_ER5010":
        return "An error occurred during the service."
    if code == "FS_CU9900":
        return "(Fanclub) This is a fanclub-only content, Fanclub not subscribed"
    if code == "FS_CU9999":
        return "Community Info is Invalid."
    if code == "FS_CJ1010":
        return "This Nickname already in use"
    if code == "FS_CJ1011":
        return "You are already a member in this community"
    if code == "FS_CJ1014":
        return "Invalid characters or spaces included, Please check input value"
    if code == "FS_CM1010":
        return "No content available, check are you in this community?"
    if code == "FS_CJ1017":
        return "You cannot join again within 24 hours you leave the community"
    if code == "FS_CU2050":
        return "This post mine be not found or deleted, Null post id."
    if code == "FS_MD9040":
        return "Join or Verify your Fanclub to enjoy various exclusive content and benefits"
    if code == "FS_ME2020":
        return "You've exceeded the code request limit. Please try again after 1 hour."
    if code == "FS_ME2050":
        return "OTP code does not match. Please try again"
    if code == "FS_ER5010":
        return "This account may not be registered in the Berriz database"
    if code == "FS_ME1010":
        return "This email address is already registered"
    if code == "FS_ME2060":
        return "Invalid email address(Only lowercase letters)"
    if code == "FS_ER4010":
        return "Please enter a combination of alphanumeric and special characters"
    if code == "FS_AU4002":
        return "Invalid authenticateKey."
    if code == "FS_AU4030":
        return "Unfortunately, your account has been suspended. Additional authentication is required to re-enable"
    if code == "FS_CU9910":
        return "Fanclub not subscribed or current not login."
    if code == "FS_CT2010":
        return "Comment not found or deleted."
    if code == "FS_CT1010":
        return "Fail to process comment"
    return code

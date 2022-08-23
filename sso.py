import time
import requests
import json
import traceback
import functools
from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
    TimeoutException,
)


def results_info(f):
    """ log executions time and better format some result status of the function passed as a parameter
    Args:
        f (function): method
    Returns:
        function: decorated function
    """
    @functools.wraps
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        result = f(self, *args, **kwargs)
        execution_time = time.time() - start_time
        response = {
            "body": {
                "execution": {
                    "status": result.get("operation_status"),
                    "execution_time": execution_time,
                    "jobs": {
                        "status": f"{result.get('operation_name')} with {result.get('data')}",
                        "result": f"Erros: {result.get('error')}",
                    },
                }
            }
        }
        self.driver.close()
        return response
    return wrapper


class SSO:
    user_management_url = "https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/users",
    binary_path = r"/opt/chrome",
    chromedriver_path = r"/opt/chromedriver",

    def __init__(
        self,
        username="username",
        password="password",
        account_id="account_id",
    ):
        self.__username = username
        self.__password = password
        self.__account_id = account_id
        self.__url = f"https://{self.__account_id}.signin.aws.amazon.com/console",

        print("Configuring chrome options... \n")

        options = Options()
        options.binary_location = self.binary_path
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x1696")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument("--lang=en")
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")

        print("Options configured...\nStarting chrome...\n")
        self.driver = webdriver.Chrome(
            executable_path=self.chromedriver_path, options=options
        )
        self.wait = WebDriverWait(self.driver, 30)
        print("Chrome started!\n")

    @results_info
    def login(self):
        """Log in to AWS console"

        Returns:
            bool || dict: True if successfully logged in, and a dict with execution data otherwise
        """
        print("___________logging in at AWS_________\n")
        try:
            self.driver.get(self.__url)
            username_input_element = self.wait.until(
                EC.element_to_be_clickable((By.ID, "username"))
            )
            password_input_element = self.wait.until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "signin_button"))
            )
            username_input_element.clear()
            password_input_element.clear()
            username_input_element.send_keys(self.__username)
            password_input_element.send_keys(self.__password)
            submit_button.click()
            self.wait.until(EC.title_is("AWS Management Console"))
        except (TimeoutException, NoSuchElementException, WebDriverException) as error:
            msg = f"{traceback.format_exc()}\n{error}"
            print("Something went wrong during login process\n")
            return {
                "error": msg,
                "operation_name": "AWS SSO Login",
                "operation_status": "incomplete",
                "data": [self.__username, self.__password, self.__url],
            }
        else:
            print("logged in at AWS SSO\n")
            return True

    def get_user_password(self):
        """retrieve the AWS SSO generated password 

        Returns:
            string || dict: return the user password if nothing goes wrong. Otherwise, returns a dict with some execution info.
        """
        print("retrieving user password...\n")
        try:
            clipboard_area_element = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, "otp-clipboard-area-copy"))
            )
            show_password_input_element = clipboard_area_element.find_element(
                By.TAG_NAME, "input"
            )
            show_password_input_element.click()
            user_sso_password = self.driver.find_element(
                By.XPATH,
                "//*[@id='OTP-generation-modal']/div[3]/div/div/div[2]/div/div[3]/div/div[1]/div/div/div[3]/div[2]",
            ).text
        except (NoSuchElementException, TimeoutException) as e:
            error = f"Erro: {traceback.format_exc()}\n{e}"
            print("Something went wrong while retrieving user password")
            return {
                "operation_status": "incomplete",
                "error": error,
                "operation_name": "Get User Password",
            }
        user_sso_password = user_sso_password.replace("Hide password", "")
        print(f"password : {user_sso_password}")
        return user_sso_password

    def add_user_to_groups(self, user_groups):
        """Add user to AWS SSO groups

        Args:
            user_groups (list): list containing the groups

        Returns:
            boll || dict: True if groups are add to user successfully. Otherwise, returns a dict with some execution info.
        """
        print("Adding user to groups...\n")
        try:
            if user_groups:
                time.sleep(3)
                available_groups_table_element = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//*[@id="sso-groups-main-table"]/div[2]/div[1]/table/tbody',
                        )
                    )
                )
                time.sleep(3)
                table_rows = available_groups_table_element.find_elements(
                    By.TAG_NAME, "tr"
                )
                for line in table_rows:
                    group = line.find_element(By.TAG_NAME, "a").text
                    if group in user_groups:
                        line.find_element(By.TAG_NAME, "input").click()
            else:
                print(" No groups Provided! Adding user without groups...")

            nextPage_button_element = self.driver.find_element(
                By.XPATH,
                '//*[@id="add-user-wizard"]/div/div/div[2]/div[3]/div/div/div/div/div[3]/button',
            )
            nextPage_button_element.click()
            time.sleep(4)
            addUser_button_element = self.driver.find_element(
                By.XPATH,
                '//*[@id="add-user-wizard"]/div/div/div[2]/div[3]/div/div/div/div/div[3]/button',
            )
            addUser_button_element.click()
            return True
        except (NoSuchElementException, TimeoutException) as e:
            error = f"Erro: {traceback.format_exc()}\n{e}"
            operation_status = "incomplete"
            return {
                "operation_status": operation_status,
                "error": error,
                "operation_name": "Add User to Groups",
            }

    def parse_input_data(self, data):
        """Auxiliary method to parse the input data

        Args:
            data (dict): with the user details

        Returns:
            Tuple: all data separated in its own corresponding variable
        """
        try:
            user_data = data["body"]["services"]
            email = user_data[0].get("input").get("users")[0].get("email")
            first_name = user_data[0].get("input").get("users")[
                0].get("firstname")
            last_name = user_data[0].get("input").get("users")[
                0].get("lastname")
            groups = user_data[0].get("input").get("users")[0].get("groups")
            parsed_data = (email, first_name, last_name, groups)
            return parsed_data
        except (AttributeError, KeyError):
            print(
                "Something went wrong while parsing the input json. It  the keys or its structure may have changed\n")

    @results_info
    def create_user(self, user_data):
        """Create user at AWS SSO with de data provided

        Args:
            message (dict): user data needed to do so

        Returns:
            dict: execution info
        """
        print("---------creating user----------\n")
        parsed_data = self.parse_input_data(user_data)
        email, first_name, last_name, groups = parsed_data
        print("Navigating to user management console...\n")
        try:
            self.driver.get(self.user_management_url)
            add_user_button = self.wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//a[@data-testid='add-user-button']")
                )
            )
            add_user_button.click()
            self.wait.until(
                EC.url_to_be(
                    "https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/users$addUserWizard"
                )
            )
            root_div_element = self.wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "user-profile-create-edit-form")
                )
            )
            username_element = root_div_element.find_element(
                By.XPATH, "//input[@placeholder='Enter username']"
            )
            generate_password_checkbox = root_div_element.find_element(
                By.XPATH, "//input[@value='OTP']"
            )
            email_elements = root_div_element.find_elements(
                By.XPATH, "//input[@placeholder='email@example.com']"
            )
            first_name_element = root_div_element.find_element(
                By.XPATH, "//input[@placeholder='Enter first name']"
            )
            last_name_element = root_div_element.find_element(
                By.XPATH, "//input[@placeholder='Enter last name']"
            )
            next_button_element = self.driver.find_element(
                By.XPATH,
                '//*[@id="add-user-wizard"]/div/div/div[2]/div[3]/div/div/div/div/div[2]/button',
            )
            email_element = email_elements[0]
            confirm_email_element = email_elements[1]
            username_element.clear()
            email_element.clear()
            confirm_email_element.clear()
            first_name_element.clear()
            last_name_element.clear()
            generate_password_checkbox.click()
            email_element.send_keys(email)
            username_element.send_keys(email)
            confirm_email_element.send_keys(email)
            first_name_element.send_keys(first_name)
            if last_name:
                last_name_element.send_keys(last_name)
            else:
                # if user wasn't created with lastname on GCC, create aws-sso use account with last name as 'colaborador'
                last_name_element.send_keys("colaborador")
            next_button_element.click()
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            error = f"Erro: {traceback.format_exc()}\n{e}"
            operation_status = "incomplete"
            operation_name = "Create User"
        result_add_user_to_groups = self.add_user_to_groups(groups)
        if result_add_user_to_groups:
            result_get_user_password = self.get_user_password()
            if type(result_get_user_password) == str:
                print("User Password was successfully collected")
        else:
            error = result_add_user_to_groups.get("error")
            operation_name = "Create User - Add User to Groups"
            operation_status = result_add_user_to_groups.get(
                "operation_status")
        return {
            "error": error,
            "operation_name": operation_name,
            "operation_status": operation_status,
            "data": user_data,
        }

    @results_info
    def update_user(self, user_data):
        """Update user info at AWS SSo

        Args:
            user_data (dict): User data needed to do so

        Returns:
            dict: execution info
        """
        try:
            self.driver.get(self.user_management_url)
            username = user_data[0][0].get("input").get("users")[
                0].get("email")
            first_name = user_data[0][0].get("input").get("users")[
                0].get("firstname")
            last_name = user_data[0][0].get("input").get("users")[
                0].get("lastname")
            display_name = (
                user_data[0][0].get("input").get("users")[
                    0].get("display_name")
            )
            # Pega todos os usernames
            users_tbody_element = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[@id='sso-users-main-table']/div[2]/div[1]/table/tbody",
                    )
                )
            )
            users = users_tbody_element.find_elements(
                By.PARTIAL_LINK_TEXT, "@mapia.ai")
            # Procura o usuário e se achar, clica em editar e edita o campo desejado com o novo valor
            for user in users:
                if username in user.text:
                    user.click()
                    profile_details_div_element = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.ID, "user-profile-overview-card-header-container")
                        )
                    )
                    editButton_element = profile_details_div_element.find_element(
                        By.TAG_NAME, "a"
                    )
                    editButton_element.click()
                    firstName_input_element = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//input[@placeholder='Enter first name']")
                        )
                    )
                    lastName_input_element = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//input[@placeholder='Enter last name']")
                        )
                    )
                    displayName_input_element = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//input[@placeholder='Enter display name']")
                        )
                    )
                    firstName_input_element.clear()
                    lastName_input_element.clear()
                    displayName_input_element.clear()
                    firstName_input_element.send_keys(first_name)
                    lastName_input_element.send_keys(last_name)
                    displayName_input_element.send_keys(display_name)
                    submitButton_element = self.driver.find_element(
                        By.XPATH, "//span[text()='Save changes']"
                    )
                    submitButton_element.click()

                print("Usuário atualizado")
            else:
                print("Usuário não cadastrado no SSO")
            operation_status = "complete"
            error = None
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            error = f"Erro: {traceback.format_exc()}\n{e}"
            operation_status = "incomplete"
        return {
            "error": error,
            "operation_name": "Update User",
            "operation_status": operation_status,
            "data": user_data,
        }

    @results_info
    def delete_user(self, username):
        """Delete user at AWS SSO

        Args:
            username (string): email of the user you want to delete

        Returns:
            dict: execution info
        """
        print("Deleting user....\n")
        try:
            self.driver.get(self.user_management_url)
            users_tbody_element = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[@id='sso-users-main-table']/div[2]/div[1]/table/tbody",
                    )
                )
            )
            table_rows_elements = users_tbody_element.find_elements(
                By.TAG_NAME, "tr")
            for row in table_rows_elements:
                if username in row.text:
                    check_box_element = row.find_element(By.TAG_NAME, "input")
                    check_box_element.click()
                else:
                    print("usuário não está no SSO\n")
            # deleta e confirma a remoção
            delete_button_element = self.driver.find_element(
                By.XPATH, "//button[@data-testid='delete-user-button']"
            )
            delete_button_element.click()

            confirm_delete_span_element = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[text()='Delete user']"))
            )
            confirm_delete_span_element.click()
            print("usuário deletado\n")
            operation_status = "complete"
            error = None
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            print("Something went wrong while deleting user\n")
            error = f"Error {traceback.format_exc()}\n{e}"
            operation_status = "incomplete"
        return {
            "error": error,
            "operation_name": "Delete User",
            "operation_status": operation_status,
            "data": username,
        }

    def enable_disable_user(self, user_data):
        # self.driver.get(url)
        username = user_data["username"]

        self.driver.get(self.user_management_url)
        user = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, username))
        ).click()

        status_button = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="user-overview-card"]/div[2]/div/div/div/div[1]/div/div/div[2]/div[2]/span/button',
                )
            )
        ).click()

        status_text = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="user-overview-card"]/div[2]/div/div/div/div[1]/div/div/div[2]/div[2]/span/span/div/div[2]',
                )
            )
        ).text
        status = status_text.split()[0]

        if (
            status == "Disabled"
            and action == "Disable"
            or status == "Enabled"
            and action == "Enable"
        ):
            print("Nenhuma ação necessária.")

        elif status == "Enabled" or "Habilitado" and action == "Disable":

            disable_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="user-overview-card-header"]/div[2]/div/div/button',
                    )
                )
            ).click()

            confirm_disable_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="disable-user-modal"]/div[3]/div/div/div[3]/div/div/div[2]/button',
                    )
                )
            ).click()

        elif status == "Disabled" or "Desabilitado" and action == "Enable":
            disable_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="user-overview-card-header"]/div[2]/div/div/button',
                    )
                )
            ).click()

            confirm_enable_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="enable-user-modal"]/div[3]/div/div/div[3]/div/div/div[2]/button/span',
                    )
                )
            ).click()

    def sso_group_checker(self, data):
        modules = data["groups"]
        username = data["email"]
        self.driver.get(self.user_management_url)

        self.driver.get(
            "https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/users"
        )
        user = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, username))
        ).click()
        groups_button = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="app"]/div/div/div/div/main/div/div[3]/div/div/div/div[4]/div/div[1]/span/ul/li[2]/button',
                )
            )
        ).click()
        user_groups = self.driver.find_element(
            By.XPATH, '//*[@id="sso-groups-main-table"]/div[2]/div[1]/table/tbody'
        )

        current_groups = []
        time.sleep(1)
        for line in user_groups.find_elements(By.TAG_NAME, "tr"):
            current_groups.append(line.find_element(By.TAG_NAME, "a").text)
        for user_groups in current_groups:
            if current_groups not in modules:
                line.find_element(By.TAG_NAME, "input").click()
                remove_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//*[@id="sso-groups-main-table"]/div[1]/div/div[1]/div[2]/div/div[1]/button/span',
                        )
                    )
                ).click()
                confirm_remove_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "/html/body/div[5]/div/div[3]/div/div/div[3]/div/div/div[2]/button/span",
                        )
                    )
                ).click()
        self.driver.refresh()
        updated_page_user_groups = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 '//*[@id="sso-groups-main-table"]/div[2]/div[1]/table/tbody')
            )
        )
        updated_current_groups = []
        time.sleep(1)
        for line in updated_page_user_groups.find_elements(By.TAG_NAME, "tr"):
            updated_current_groups.append(
                line.find_element(By.TAG_NAME, "a").text)
        missing_groups = set(modules).difference(updated_current_groups)
        if missing_groups:
            for element in missing_groups:
                all_groups_page = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//*[@id="sso-groups-main-table"]/div[1]/div/div[1]/div[2]/div/div[2]/a/span',
                        )
                    )
                ).click()
                search_field = self.wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH,
                         "//input[@placeholder='Find groups by group name']")
                    )
                )
                search_field.clear()
                search_field.send_keys(element)
                group_field = self.wait.until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            '//*[@id="sso-groups-main-table"]/div[2]/div[1]/table/tbody',
                        )
                    )
                )
                time.sleep(1)
                group_field.find_element(By.TAG_NAME, "input").click()

                add_user_to_group = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//*[@id="app"]/div/div/div/div/main/div/div[3]/div/div/div/div[3]/div/div/div[2]/button',
                        )
                    )
                ).click()
                time.sleep(1)

    def create_zendesk_ticket(self, message):
        """create a zendesk ticket informing what went wrong in the operation, based on the execution result provided by the decorator
        Args:
            message (dict): containg the execution status data
        """
        # request params
        url = "url"
        user = "user"
        pwd = "pwd"
        headers = {"content-type": "application/json"}
        # ticket infos
        subject = f"SSO automation Failed"
        body = (
            f" Erro na operação: \n"
            + f"{message.get('body').get('execution').get('jobs').get('status')} \n"
            + f"Com a mensagem :\n {message.get('body').get('execution').get('jobs').get('result')}"
        )
        data = {"ticket": {"subject": subject, "comment": {"body": body}}}
        payload = json.dumps(data)
        response = requests.post(
            url, data=payload, auth=(user, pwd), headers=headers)
        if response.status_code != 201:
            print("Status:", response.status_code,
                  "Problem with the request. Exiting.")
            exit()
        print("Successfully created the ticket.")

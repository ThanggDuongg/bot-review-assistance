from code_review_agent.code_review_agent import run_pipeline
import json
from langchain_core.documents import Document

def fetch_pr_diff():
    return '''diff --git a/Services/UserService.cs b/Services/UserService.cs
        index e69de29..a3dcb23 100644
        --- a/Services/UserService.cs
        +++ b/Services/UserService.cs
        @@ class UserService {
        +    private readonly IUserRepository _userRepository;
        +    private readonly IEmailService _emailService;
        +    public UserService(IUserRepository userRepository, IEmailService emailService) {
        +        _userRepository = userRepository;
        +        _emailService = emailService;
        +    }
        +
        +    public User GetUser(int id) {
        +        return _userRepository.FindById(id);
        +    }
        +
        +    public void DeleteUser(int id) {
        +        _userRepository.Delete(id);
        +        _emailService.SendUserDeletedNotification(id);
        +    }
        +
        +    public List<User> GetAllUsers() {
        +        return _userRepository.FindAll();
        +    }
        +
        +    public void CreateUser(User user) {
        +        _userRepository.Save(user);
        +        _emailService.SendWelcomeEmail(user.Email);
        +    }
        }
        
        diff --git a/Controllers/UserController.cs b/Controllers/UserController.cs
        index e69de29..b2fda34 100644
        --- a/Controllers/UserController.cs
        +++ b/Controllers/UserController.cs
        @@ class UserController : Controller {
        +    private readonly UserService _userService;
        +    public UserController(UserService userService) {
        +        _userService = userService;
        +    }
        +
        +    [HttpGet("/user/{id}")]
        +    public IActionResult GetUser(int id) {
        +        var user = _userService.GetUser(id);
        +        if (user == null) return NotFound();
        +        return Ok(user);
        +    }
        +
        +    [HttpDelete("/user/{id}")]
        +    public IActionResult DeleteUser(int id) {
        +        _userService.DeleteUser(id);
        +        return NoContent();
        +    }
        +
        +    [HttpPost("/user")]
        +    public IActionResult CreateUser([FromBody] User user) {
        +        _userService.CreateUser(user);
        +        return Created($"/user/{user.Id}", user);
        +    }
        +
        +    [HttpGet("/users")]
        +    public IActionResult GetAllUsers() {
        +        var users = _userService.GetAllUsers();
        +        return Ok(users);
        +    }
        }'''

def make_json_serializable(obj):
    """Convert objects to JSON serializable format."""
    if isinstance(obj, Document):
        return {
            "page_content": obj.page_content,
            "metadata": obj.metadata
        }
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj

if __name__ == "__main__":
    diff = fetch_pr_diff()
    result = run_pipeline(diff)
    print("Full Review Result (JSON):")

    # Convert to JSON serializable format
    serializable_result = make_json_serializable(result)
    print(json.dumps(serializable_result, indent=2))

example_diff = '''### File: 'src/app/user/user.component.ts'
@@ -1,25 +1,45 @@
-import { Component, OnInit } from '@angular/core';
-import { HttpClient } from '@angular/common/http';
+import { Component, OnInit, OnDestroy } from '@angular/core';
+import { ActivatedRoute } from '@angular/router';
+import { Subject, takeUntil } from 'rxjs';
+import { UserService } from './user.service';
+import { User } from './models/user.model';

@Component({
-  selector: 'app-old-user',
+  selector: 'app-user',
-  template: `
-    <div>Old template</div>
-  `
+  templateUrl: './user.component.html',
+  styleUrls: ['./user.component.scss']
})
-export class UserComponent implements OnInit {
-  user: any;
-  constructor(private http: HttpClient) {}
+export class UserComponent implements OnInit, OnDestroy {
+  user: User | null = null;
+  loading = false;
+  error: string | null = null;
+  private destroy$ = new Subject<void>();

+  constructor(
+    private route: ActivatedRoute,
+    private userService: UserService
+  ) {}

  ngOnInit(): void {
-    // old init
-    this.http.get('/user/1').subscribe(data => this.user = data);
+    this.loading = true;
+    this.route.params
+      .pipe(takeUntil(this.destroy$))
+      .subscribe(params => {
+        const userId = +params['id'];
+        this.loadUser(userId);
+      });
  }

+  ngOnDestroy(): void {
+    this.destroy$.next();
+    this.destroy$.complete();
+  }
+
+  private loadUser(userId: number): void {
+    this.userService.getUserWithOrders(userId)
+      .pipe(takeUntil(this.destroy$))
+      .subscribe({
+        next: (user) => {
+          this.user = user;
+          this.loading = false;
+        },
+        error: (err) => {
+          this.error = 'Failed to load user data';
+          this.loading = false;
+        }
+      });
+  }
}

### File: 'src/app/user/user.component.html'
@@
+<div class="user-container" *ngIf="!loading && !error">
+  <div class="user-header">
+    <h2>{{ user?.name }}</h2>
+    <span class="user-id">#{{ user?.id }}</span>
+  </div>
+
+  <div class="user-stats">
+    <div class="stat-card">
+      <span class="stat-label">Total Orders</span>
+      <span class="stat-value">{{ user?.orders?.length || 0 }}</span>
+    </div>
+    <div class="stat-card">
+      <span class="stat-label">Total Spent</span>
+      <span class="stat-value">{{ user?.totalSpent | currency }}</span>
+    </div>
+  </div>
+
+  <div class="orders-section">
+    <h3>Recent Orders</h3>
+    <div class="order-list">
+      <div class="order-item" *ngFor="let order of user?.orders">
+        <div class="order-header">
+          <span class="order-id">#{{ order.id }}</span>
+          <span class="order-date">{{ order.createdAt | date }}</span>
+        </div>
+        <div class="order-details">
+          <span class="order-item-name">{{ order.itemName }}</span>
+          <span class="order-price">{{ order.price | currency }}</span>
+        </div>
+      </div>
+    </div>
+  </div>
+</div>
+
+<div class="loading-spinner" *ngIf="loading">
+  <mat-spinner></mat-spinner>
+</div>
+
+<div class="error-message" *ngIf="error">
+  <mat-icon>error</mat-icon>
+  <span>{{ error }}</span>
+</div>

### File: 'src/app/user/user.component.scss'
@@
+.user-container {
+  padding: 20px;
+  max-width: 800px;
+  margin: 0 auto;
+}
+
+.user-header {
+  display: flex;
+  align-items: center;
+  gap: 12px;
+  margin-bottom: 24px;
+  
+  h2 {
+    margin: 0;
+    color: #333;
+  }
+  
+  .user-id {
+    color: #666;
+    font-size: 14px;
+  }
+}
+
+.user-stats {
+  display: grid;
+  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
+  gap: 16px;
+  margin-bottom: 32px;
+}
+
+.stat-card {
+  background: #f8f9fa;
+  padding: 16px;
+  border-radius: 8px;
+  text-align: center;
+  
+  .stat-label {
+    display: block;
+    font-size: 12px;
+    color: #666;
+    text-transform: uppercase;
+    margin-bottom: 4px;
+  }
+  
+  .stat-value {
+    display: block;
+    font-size: 24px;
+    font-weight: bold;
+    color: #333;
+  }
+}
+
+.orders-section {
+  h3 {
+    margin-bottom: 16px;
+    color: #333;
+  }
+}
+
+.order-list {
+  display: flex;
+  flex-direction: column;
+  gap: 12px;
+}
+
+.order-item {
+  background: white;
+  border: 1px solid #e0e0e0;
+  border-radius: 8px;
+  padding: 16px;
+  
+  .order-header {
+    display: flex;
+    justify-content: space-between;
+    margin-bottom: 8px;
+    
+    .order-id {
+      font-weight: bold;
+      color: #333;
+    }
+    
+    .order-date {
+      color: #666;
+      font-size: 14px;
+    }
+  }
+  
+  .order-details {
+    display: flex;
+    justify-content: space-between;
+    align-items: center;
+    
+    .order-item-name {
+      color: #333;
+    }
+    
+    .order-price {
+      font-weight: bold;
+      color: #2e7d32;
+    }
+  }
+}

### File: 'src/app/user/user.service.ts'
@@ -1,15 +1,25 @@
 import { Injectable } from '@angular/core';
 import { HttpClient } from '@angular/common/http';
-import { Observable } from 'rxjs';
+import { Observable } from 'rxjs';
+import { User } from './models/user.model';
+import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class UserService {
-  constructor(private http: HttpClient) {}
+  private readonly apiUrl = `${environment.apiUrl}/users`;

-  // Old method - removed
-  getUser(id: number): Observable<any> {
-    return this.http.get(`/api/users/${id}`);
-  }
+  constructor(private http: HttpClient) {}

+  getUserWithOrders(userId: number): Observable<User> {
+    return this.http.get<User>(`${this.apiUrl}/${userId}/orders`);
+  }
+
+  getUserProfile(userId: number): Observable<User> {
+    return this.http.get<User>(`${this.apiUrl}/${userId}`);
+  }
+
+  updateUserProfile(userId: number, updates: Partial<User>): Observable<User> {
+    return this.http.patch<User>(`${this.apiUrl}/${userId}`, updates);
+  }
}

### File: 'Backend/Controllers/UserController.cs'
@@ -1,20 +1,35 @@
 using Microsoft.AspNetCore.Mvc;
-using Services;
+using Microsoft.AspNetCore.Authorization;
+using MediatR;
+using Application.Users.Queries;
+using Application.Users.Commands;
+using Application.Common.Models;

-namespace Controllers {
+namespace Backend.Controllers {
     [ApiController]
-    [Route("[controller]")]
+    [Route("api/[controller]")]
+    [Authorize]
     public class UserController : ControllerBase {
-        private readonly UserService _userService;
-        public UserController() {
-            _userService = new UserService(); // for demo only
-        }
+        private readonly IMediator _mediator;

+        public UserController(IMediator mediator) {
+            _mediator = mediator;
+        }

         [HttpGet("{id}")]
-        public IActionResult GetUser(int id) {
-            return Ok(_userService.GetUserWithOrders(id));
+        public async Task<ActionResult<UserDto>> GetUser(int id) {
+            var query = new GetUserQuery { UserId = id };
+            var result = await _mediator.Send(query);
+            return Ok(result);
         }
+
+        [HttpGet("{id}/orders")]
+        public async Task<ActionResult<UserWithOrdersDto>> GetUserWithOrders(int id) {
+            var query = new GetUserWithOrdersQuery { UserId = id };
+            var result = await _mediator.Send(query);
+            return Ok(result);
+        }
+
+        [HttpPatch("{id}")]
+        public async Task<ActionResult<UserDto>> UpdateUser(int id, [FromBody] UpdateUserCommand command) {
+            command.UserId = id;
+            var result = await _mediator.Send(command);
+            return Ok(result);
+        }
     }
 }

### File: 'Backend/Application/Users/Queries/GetUserWithOrdersQuery.cs'
@@ -1,35 +1,35 @@
 using MediatR;
 using Application.Common.Interfaces;
 using Application.Common.Models;
 using AutoMapper;
 using Microsoft.EntityFrameworkCore;

 namespace Application.Users.Queries {
     public class GetUserWithOrdersQuery : IRequest<UserWithOrdersDto> {
         public int UserId { get; set; }
     }

     public class GetUserWithOrdersQueryHandler : IRequestHandler<GetUserWithOrdersQuery, UserWithOrdersDto> {
         private readonly IUserRepository _userRepository;
         private readonly IOrderRepository _orderRepository;
         private readonly IMapper _mapper;

         public GetUserWithOrdersQueryHandler(
             IUserRepository userRepository,
             IOrderRepository orderRepository,
             IMapper mapper) {
             _userRepository = userRepository;
             _orderRepository = orderRepository;
             _mapper = mapper;
         }

         public async Task<UserWithOrdersDto> Handle(GetUserWithOrdersQuery request, CancellationToken cancellationToken) {
-            // N+1 Issue: Loading user and orders separately
-            var user = await _userRepository.GetByIdAsync(request.UserId);
-            if (user == null) {
-                throw new NotFoundException($"User with ID {request.UserId} not found");
-            }
-
-            var orders = await _orderRepository.GetOrdersByUserIdAsync(request.UserId);
-            var totalSpent = orders.Sum(o => o.Price);
-
-            var userDto = _mapper.Map<UserDto>(user);
-            var orderDtos = _mapper.Map<List<OrderDto>>(orders);
-
-            return new UserWithOrdersDto {
-                Id = userDto.Id,
-                Name = userDto.Name,
-                Email = userDto.Email,
-                CreatedAt = userDto.CreatedAt,
-                Orders = orderDtos,
-                TotalSpent = totalSpent
-            };
+            // Fixed N+1: Use single query with Include
+            var user = await _userRepository.GetByIdWithOrdersAsync(request.UserId);
+            if (user == null) {
+                throw new NotFoundException($"User with ID {request.UserId} not found");
+            }
+
+            var totalSpent = user.Orders.Sum(o => o.Price);
+            var userDto = _mapper.Map<UserDto>(user);
+            var orderDtos = _mapper.Map<List<OrderDto>>(user.Orders);
+
+            return new UserWithOrdersDto {
+                Id = userDto.Id,
+                Name = userDto.Name,
+                Email = userDto.Email,
+                CreatedAt = userDto.CreatedAt,
+                Orders = orderDtos,
+                TotalSpent = totalSpent
+            };
         }
     }
 }

### File: 'Backend/Application/Users/Commands/UpdateUserCommand.cs'
@@ -25,15 +25,20 @@
         public async Task<UserDto> Handle(UpdateUserCommand request, CancellationToken cancellationToken) {
             var currentUserId = _currentUserService.UserId;
             
-            // Security issue: No authorization check
             var user = await _userRepository.GetByIdAsync(request.UserId);
             if (user == null) {
                 throw new NotFoundException($"User with ID {request.UserId} not found");
             }
 
+            // Security fix: Add authorization check
+            if (currentUserId != request.UserId && !_currentUserService.HasRole("admin")) {
+                throw new UnauthorizedAccessException("You can only update your own profile");
+            }
+
             user.Name = request.Name;
             user.Email = request.Email;
+            user.UpdatedAt = DateTime.UtcNow;

             await _userRepository.UpdateAsync(user);
             return _mapper.Map<UserDto>(user);
         }
     }
 }

### File: 'Backend/Infrastructure/Data/UserRepository.cs'
@@ -15,10 +15,15 @@
         public async Task<User> GetByIdAsync(int id) {
             return await _context.Users
                 .FirstOrDefaultAsync(u => u.Id == id);
         }

+        public async Task<User> GetByIdWithOrdersAsync(int id) {
+            // Fixed N+1: Include orders in single query
+            return await _context.Users
+                .Include(u => u.Orders)
+                .FirstOrDefaultAsync(u => u.Id == id);
+        }
+
         public async Task<List<User>> GetAllAsync() {
             return await _context.Users.ToListAsync();
         }
'''

# Custom Bitbucket format with line numbers
example_custom_bitbucket_diff = '''
## File: 'Backend/Controllers/ProductController.cs'
- 3     public IActionResult GetProductReviews(int id) {
- 4         var productWithReviews = _productRepository.GetByIdWithReviews(id); // Eager load
- 5         if (productWithReviews == null) return NotFound();
- 6         return Ok(productWithReviews.Reviews);
+ 3     public IActionResult GetProductReviews(int id) {
+ 4         var product = _productRepository.GetById(id);
+ 5         var reviews = new List<Review>();
+ 6         foreach (var reviewId in product.ReviewIds) {
+ 7             reviews.Add(_reviewRepository.GetById(reviewId)); // N+1 query
+ 8         }
+ 9         return Ok(reviews);
+ 10     }
'''
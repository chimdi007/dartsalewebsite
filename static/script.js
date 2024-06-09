function showDashpage(pageId) {
    document.querySelectorAll(".dashpage").forEach((dashpage) => {
      dashpage.style.display = "none";
    });
    document.getElementById(pageId).style.display = "block";
  }

  function homePage(pageId) {
    document.querySelectorAll(".dashpage").forEach((dashpage) => {
      dashpage.style.display = "none";
    });
    document.getElementById(pageId).style.display = "block";
    location.reload()
  }

  function showShoppage(pageId) {
    document.querySelectorAll(".shoppage").forEach((shoppage) => {
      shoppage.style.display = "none";
    });
    document.getElementById(pageId).style.display = "block";
  }

  function openInvForm() {
    document.getElementById("invForm-container").style.display = "block";
    document.getElementById("overlay").style.display = "block";
  }

  function closeInvForm() {
    document.getElementById("invForm-container").style.display = "none";
    document.getElementById("overlay").style.display = "none";
  }

  document.getElementById('cpw').addEventListener('click', function() {
    var form = document.getElementById('resetForm');
    var btn = document.getElementById('cpw')
    if (form.style.display === 'none') {
        btn.style.display = 'block'
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
        btn.style.display = 'block'
    }
});

function createNewShop(event) {
    event.preventDefault();
    
    // Collect the form data
    let shop_name = document.getElementById('newShopName').value;
    let shop_password = document.getElementById('newShopPassword').value;
    let subscription = document.getElementById('subscription').value;
    let promo_code = document.getElementById('promoCode').value;
    let email = document.getElementById('clientEmail').value;
    let unique_id = document.getElementById('clientUniqueID').value;
    let url = '/create_shop';  // Ensure this URL matches your Flask route

    // Create the data object to send in the request
    let data = {
        shop_name: shop_name,
        shop_password: shop_password,
        subscription: subscription,
        promo_code: promo_code,
        email: email,
        unique_id: unique_id
    };

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response received:", data);
        if (data.ok) {
            alert(data.message);
            location.reload();
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.text);
    });
}


function changePassword(){
    let email = document.getElementById('clientEmail').value;
    let old_password = document.getElementById('op').value;
    let new_password = document.getElementById('np').value;
    let url = "/change_password";

    data = {
        email: email,
        old_password: old_password,
        new_password: new_password
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response received:", data);
        if (data.ok) {
            alert(data.message);
            location.reload();
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.text);
    });
}

document.getElementById('create-user-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    let name = document.getElementById('name').value;
    let username = document.getElementById('username').value;
    let accessLevel = document.getElementById('access_level').value;
    let password = document.getElementById('password').value;
    let user_unique_id = document.getElementById('new-user_unique_id').value;
    let shop_key = document.getElementById('new-shop_key').value;
    let shop_password = document.getElementById('new-shop_password').value;

    let data = {
        name: name,
        username: username,
        access_level: accessLevel,
        password: password,
        user_unique_id: user_unique_id,
        shop_key: shop_key,
        shop_password: shop_password
    };

    fetch('/create_new_user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            alert(data.message);
            location.reload();
        } else {
            document.getElementById('message').textContent = data.message;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('message').textContent = 'An error occurred. Please try again later.';
    });
});


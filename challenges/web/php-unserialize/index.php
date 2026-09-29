<?php
// Legacy portal -- source handout. The session cookie is base64(serialize($obj))
// and is fed straight into unserialize(). A guest cookie was captured
// (session_cookie.b64). The maintenance seed below was left in this file.

$SEED = "rot-2026-maintenance"; // maintenance reveal seed (do not ship!)

// The flag never appears in the clear. FlagReveal::__wakeup() decrypts it with
// a keystream derived from its $seed the moment such an object is unserialized.
class FlagReveal {
    public $seed;
    private $sealed_hex = "60695124c179f826d199c455c052d85afca83cfe5770c9bf3a9d702d4ca078c118b04793cab2e3728ac4b1a4e767236fea";

    public function __wakeup() {
        $ct = hex2bin($this->sealed_hex);
        $out = "";
        for ($i = 0; $i < strlen($ct); $i++) {
            $blk = intdiv($i, 16);
            $ks  = md5($this->seed . ":" . $blk, true);
            $out .= $ct[$i] ^ $ks[$i % 16];
        }
        echo $out; // printed during page render
    }
}

class Session {
    public $uid;
    public $role;
}

// VULNERABLE: attacker-controlled cookie is deserialized without a class
// allowlist, so any class in scope (including FlagReveal) can be instantiated.
$raw = base64_decode($_COOKIE["sess"]);
$obj = unserialize($raw);

if ($obj instanceof Session && $obj->role === "admin") {
    echo "welcome admin";
}
?>

// java-cafe -- reverse challenge source (compiled to Vault.class; not shipped).
//
// The flag is never stored in plaintext. B is base64( xor(flag, K) ); the
// program decodes and un-xors it only to compare against the user's guess.
import java.util.Base64;

public class Vault {
    static final String B = "JCIiJxgLEAg1Aw8VUAIJAQ8+HxI8EwMEDgAUDQYc";
    static final String K = "javacafe";

    static byte[] unlock() {
        byte[] enc = Base64.getDecoder().decode(B);
        byte[] key = K.getBytes();
        byte[] out = new byte[enc.length];
        for (int i = 0; i < enc.length; i++) {
            out[i] = (byte) (enc[i] ^ key[i % key.length]);
        }
        return out;
    }

    public static void main(String[] args) {
        String flag = new String(unlock());
        System.out.println("=== java-cafe vault ===");
        if (args.length > 0 && args[0].equals(flag)) {
            System.out.println("[+] correct");
        } else {
            System.out.println("[-] nope");
        }
    }
}

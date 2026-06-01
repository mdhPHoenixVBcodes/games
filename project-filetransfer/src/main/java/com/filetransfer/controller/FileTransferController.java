@PostMapping("/connect")
public ResponseEntity<String> connect(@RequestParam String sender, @RequestParam String receiver) {
    if (registry.containsKey(receiver) && "waiting".equals(registry.get(receiver))) {
        registry.put(receiver, "connected");
        registry.put(sender, "connected");
        return ResponseEntity.ok("Connection established");
    }
    return ResponseEntity.status(404).body("User not found or not waiting");
}
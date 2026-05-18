package com.student.mcxbox;

import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketException;
import java.util.Collections;
import java.util.Enumeration;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class StartupLogger {
    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        System.out.println();
        System.out.println("MC Xbox is running.");
        System.out.println("Local: http://localhost:5000");
        printLanAddresses();
        System.out.println("If Windows Firewall prompts, allow Java on Private networks.");
        System.out.println();
    }

    private void printLanAddresses() {
        try {
            boolean found = false;
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            if (interfaces == null) {
                System.out.println("LAN: no network interfaces available");
                return;
            }
            for (NetworkInterface nif : Collections.list(interfaces)) {
                if (!nif.isUp() || nif.isLoopback() || nif.isVirtual()) {
                    continue;
                }
                for (InetAddress addr : Collections.list(nif.getInetAddresses())) {
                    String host = addr.getHostAddress();
                    if (host.contains(":")) {
                        continue;
                    }
                    found = true;
                    System.out.println("LAN: http://" + host + ":5000");
                }
            }
            if (!found) {
                System.out.println("LAN: no IPv4 address found");
            }
        } catch (SocketException e) {
            System.out.println("LAN: unable to detect address - " + e.getMessage());
        }
    }
}
